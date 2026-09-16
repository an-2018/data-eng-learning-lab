import os
os.environ['DATABASE_URL']='sqlite://'
os.environ['DEV_AUTH']='true'
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db import Base,get_db,User,Job
from app.auth import current_user
from app.content import exercises
import pytest

@pytest.fixture
def client():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session=sessionmaker(bind=engine,expire_on_commit=False)
    with Session() as db:
        db.add(User(id='u1',email='learner@example.org',role='learner'));db.commit()
    def database():
        with Session() as db:yield db
    def user():return User(id='u1',email='learner@example.org',role='learner')
    app.dependency_overrides[get_db]=database
    app.dependency_overrides[current_user]=user
    with TestClient(app) as c:yield c
    app.dependency_overrides.clear()

def test_catalog_counts(client):
    data=client.get('/tracks').json()
    assert len(data['tracks'][0]['modules'])==16
    assert len(data['tracks'][1]['modules'])==4
    assert sum(len(m['lessons']) for t in data['tracks'] for m in t['modules'])==80
    assert len(exercises())==180

def test_private_material_is_not_public(client):
    data=client.get('/exercises').json()
    for e in data:
        assert not {'solution','wrong_solutions','grading','execution','hints'} & e.keys()
        for fixture in e['fixtures']:assert 'expected' not in fixture and 'input' not in fixture
        for question in e.get('questions',[]):assert 'answer' not in question

def test_save_and_optimistic_revision(client):
    draft=client.get('/workspaces/o03-e01').json()
    files={'query.rq':'SELECT ?x WHERE { ?x ?p ?o }'}
    response=client.put('/workspaces/o03-e01',json={'files':files,'revision':draft['revision']})
    assert response.status_code==200
    assert client.get('/workspaces/o03-e01').json()['files']==files
    assert client.put('/workspaces/o03-e01',json={'files':files,'revision':draft['revision']}).status_code==409

def test_path_and_size_validation(client):
    assert client.put('/workspaces/o03-e01',json={'files':{'../escape':'x'}}).status_code==422
    assert client.put('/workspaces/o03-e01',json={'files':{'query.rq':'x'*200001}}).status_code==422

def test_hints_mark_assistance_and_reading_is_separate(client):
    assert client.post('/exercises/o03-e01/hints/0').status_code==200
    assert client.get('/workspaces/o03-e01').json()['assisted'] is True
    client.post('/lessons/o03-l1/read')
    progress=client.get('/progress').json()
    assert progress['read_lessons']==['o03-l1'] and progress['skills']==[]

def test_foreign_job_and_author_access(client):
    assert client.get('/jobs/unknown').status_code==404
    assert client.get('/author/validation').status_code==403

def test_tutor_unconfigured_remains_usable(client):
    r=client.post('/tutor/messages',json={'exercise_id':'o03-e01','question':'How does this join work?'})
    assert r.status_code==200 and r.json()['available'] is False
    assert r.json()['sources']

def test_idempotency_and_cancel(client,monkeypatch):
    from app.worker import run_job
    monkeypatch.setattr(run_job,'apply_async',lambda **kw:None)
    payload={'exercise_id':'o03-e01','files':{'query.rq':'SELECT ?x WHERE {?x ?p ?o}'}}
    a=client.post('/submissions',json=payload,headers={'Idempotency-Key':'once'})
    b=client.post('/submissions',json=payload,headers={'Idempotency-Key':'once'})
    assert a.status_code==202 and a.json()['id']==b.json()['id']
    assert client.post('/submissions',json={**payload,'files':{'query.rq':'ASK {}'}},headers={'Idempotency-Key':'once'}).status_code==409
    jid=a.json()['id']
    assert client.post('/jobs/'+jid+'/cancel').json()['status']=='canceled'

def test_assisted_assessment_is_rejected(client):
    client.post('/exercises/o03-e01/solution')
    r=client.post('/submissions',json={'exercise_id':'o03-e01','files':{'query.rq':'ASK {}'},'mode':'assessment'},headers={'Idempotency-Key':'assisted'})
    assert r.status_code==409
