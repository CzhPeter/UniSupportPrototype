import os

basedir = os.path.abspath(os.path.dirname(__file__))
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or b'WR#&f&+%78er0we=%799eww+#7^90-;s'

    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'data', 'uploads')
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app', 'data', 'data.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True

    GROQ_API_KEY = os.environ.get('GROQ_API_KEY') or "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"
    LLM_MODEL_NAME = "llama3-70b-8192"
    EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
