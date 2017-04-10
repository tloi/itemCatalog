import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class Category(Base):
    __tablename__ = 'category'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    def __init__(self, name):
        self.name = name

    @property
    def serialize(self):
        return {
            'name'  : self.name,
            'id'    : self.id,
        }

class CategoryItem(Base):
    __tablename__ = 'category_item'

    id = Column(Integer, primary_key=True)
    title = Column(String(80), nullable=False)
    description = Column(String(250), nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    def __init__(self, title, description, category_id):
        self.title = title
        self.description = description
        self.category_id = category_id

    @property
    def serialize(self):
        return {
            'id'            : self.id,
            'title'          : self.title,
            'description'   : self.description,
        }

engine = create_engine('sqlite:///catalog.db')

Base.metadata.create_all(engine)
