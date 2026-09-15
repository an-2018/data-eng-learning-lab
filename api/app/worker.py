import uuid
from datetime import timedelta
from celery import Celery
from redis import Redis
from sqlalchemy import select, update
from .config import REDIS_URL
from .db import Session, Job, Progress, now
from .content import exercise, fingerprint
from .sandbox import execute, RuntimeUnavailable, ExecutionTimeout, ExecutionCanceled, LearnerError, image_for
from .grading import compare

celery = Celery('graphlab', broker=REDIS_URL, backend=REDIS_URL)
celery.conf.update(task_acks_late=True, worker_prefetch_multiplier=1, task_reject_on_worker_lost=True,
    task_routes={'graphlab.execute': {'queue':'ontology'}},
    beat_schedule={'recover-jobs': {'task':'graphlab.recover','schedule':60.0}})

def update_progress(db, job):
    if job.kind != 'submission' or job.status != 'passed':
        return
    p = db.scalar(select(Progress).where(Progress.user_id == job.user_id, Progress.exercise_id == job.exercise_id).with_for_update())
    if not p:
        p = Progress(id=str(uuid.uuid4()),user_id=job.user_id,exercise_id=job.exercise_id,review_step=0,passed_variants=[])
        db.add(p)
    if p.last_job_id == job.id:
        return
    p.last_job_id = job.id
    if p.state != 'passed_independently' or not job.assisted:
        p.state = 'passed_with_assistance' if job.assisted else 'passed_independently'
    step = min(p.review_step or 0, 2)
    p.review_at = now() + timedelta(days=[1,7,21][step])
    p.review_step = min(step + 1, 2)
    p.passed_variants = list(set((p.passed_variants or []) + [job.exercise_id]))

@celery.task(name='graphlab.execute', bind=True, max_retries=2)
def run_job(self, jid):
    redis = Redis.from_url(REDIS_URL)
    with Session() as db:
        job = db.get(Job,jid)
        if not job or job.status not in ['queued','running'] or job.cancel_requested:
            return
        lock = redis.lock('learner:' + job.user_id,timeout=900,blocking_timeout=0)
        if not lock.acquire(blocking=False):
            raise self.retry(countdown=5, max_retries=100)
        try:
            item = exercise(job.exercise_id)
            if fingerprint(item) != job.content_hash or image_for(item['runner']) != job.runtime_version:
                raise RuntimeUnavailable('The pinned content or runtime is unavailable. Restore the version before retrying.')
            job.status, job.lease_at = 'running', now()
            job.attempts += 1
            db.commit()
            checks, public_output = [], None
            fixtures = [f for f in item['fixtures'] if job.kind == 'submission' or f.get('public')]
            def canceled():
                db.expire(job)
                return job.cancel_requested
            for index, fixture in enumerate(fixtures):
                job.lease_at = now()
                db.commit()
                actual = execute(item['runner'],job.files,fixture['input'],item['execution'],jid,canceled)
                passed = compare(actual,fixture['expected'],item['grading'])
                visible = fixture.get('public',False)
                checks.append({'name':fixture['name'] if visible else f'Private requirement {index+1}', 'passed':passed,
                    'message': 'Requirement met' if passed else fixture.get('feedback','Recheck the stated requirements and edge cases.')})
                if visible:
                    public_output = actual
            questions = item.get('questions',[])
            concept_score = sum(job.answers.get(q['id']) == q['answer'] for q in questions) / len(questions) if questions else 1
            passed = all(c['passed'] for c in checks) and concept_score >= .8
            job.status = 'canceled' if canceled() else 'passed' if passed else 'failed'
            job.feedback = {'checks':checks,'output':public_output,'concept_score':concept_score, 'message':'All required checks passed.' if passed else 'Review the feedback and try again.'}
            job.finished_at = now()
            update_progress(db,job)
            db.commit()
        except ExecutionCanceled:
            job.status,job.feedback = 'canceled', {'message':'Execution canceled.'}
            db.commit()
        except ExecutionTimeout:
            job.status,job.feedback = 'timed_out', {'message':'Execution exceeded its time allowance. This is not a semantic verdict.'}
            db.commit()
        except LearnerError as exc:
            job.status,job.feedback = 'failed', {'message':str(exc)}
            db.commit()
        except RuntimeUnavailable:
            job.status,job.feedback = 'infrastructure_error', {'message':'The isolated runtime is unavailable. Your progress has not been changed.'}
            db.commit()
            if job.attempts < 3:
                job.status = 'queued'
                db.commit()
                raise self.retry(countdown=10)
        finally:
            if lock.owned():
                lock.release()

@celery.task(name='graphlab.recover')
def recover():
    with Session() as db:
        stale = db.scalars(select(Job).where(Job.status == 'running',Job.lease_at < now()-timedelta(minutes=15))).all()
        for job in stale:
            job.status = 'queued' if job.attempts < 3 and not job.cancel_requested else 'infrastructure_error'
            db.commit()
            if job.status == 'queued':
                run_job.apply_async(args=[job.id], queue='spark' if exercise(job.exercise_id)['runner']=='spark' else 'ontology')
