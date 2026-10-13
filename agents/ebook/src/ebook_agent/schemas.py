from pydantic import BaseModel, Field


class Topic(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    angle: str = ""


class TopicList(BaseModel):
    topics: list[Topic]


class OutlineChapter(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    brief: str = Field(min_length=1)


class Outline(BaseModel):
    chapters: list[OutlineChapter]
