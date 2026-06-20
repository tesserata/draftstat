FROM python:3.12-slim

WORKDIR /app

ADD ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

ADD draftstat /app/draftstat

RUN python -m spacy download en_core_web_sm

EXPOSE 7860
CMD ["uvicorn", "draftstat.app:app", "--host", "0.0.0.0", "--port", "7860"]
