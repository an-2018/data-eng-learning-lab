import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTENT_ROOT = Path(os.getenv('CONTENT_ROOT', str(ROOT.parent / 'content')))
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./academy.db')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
PRODUCTION = os.getenv('APP_ENV', 'development') == 'production'
DEV_AUTH = os.getenv('DEV_AUTH', 'false').lower() == 'true'
if PRODUCTION and DEV_AUTH:
    raise RuntimeError('DEV_AUTH must be disabled in production')

LIMITS = {
    'sparql': (1, '1g', 15), 'shacl': (1, '1g', 15),
    'rdf': (1, '1g', 15), 'owl': (2, '2g', 60),
    'spark': (2, '4g', 120), 'ingestion': (2, '2g', 60),
}
