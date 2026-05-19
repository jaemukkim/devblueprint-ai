import os


# 테스트는 로컬 PostgreSQL 실행 여부와 분리되도록 memory repository를 사용합니다.
os.environ["REPOSITORY_BACKEND"] = "memory"
os.environ["USE_OPENAI"] = "false"
