from flask import Flask, render_template, request, redirect, url_for, jsonify
from sqlalchemy import *
from database_setup import Base, Category, CategoryItem
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

session.query(CategoryItem).delete()
session.query(Category).delete()

sample_categories = ['Soccer', 'Basketball', 'Baseball','Frisbee']

for category_name in sample_categories:
    category = Category(category_name)
    session.add(category)
session.commit()
