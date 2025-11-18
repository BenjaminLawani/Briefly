import asyncio
from unittest.mock import Mock

import pytest


async def _fake_generate_with_groq(prompt, num_of_lessons):
    return {
        "lessons": [
            {
                "lesson_number": 1,
                "title": "Sample Lesson",
                "description": "A sample lesson",
                "content": "Content",
                "key_points": [],
                "exercises": []
            }
        ]
    }


def test_generate_creates_default_profile(monkeypatch):
    # Arrange: mock DB session so query(...).filter(...).first() returns None
    mock_db = Mock()
    mock_query = Mock()
    mock_filter = Mock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = None
    mock_db.query.return_value = mock_query

    # Provide add/commit/refresh mocks so we can assert they were called
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock()

    # Patch async AI generator and Mongo collection insert by importing the utils module
    import importlib
    import sys, os
    # Ensure project root is on sys.path so 'src' package can be imported
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    utils = importlib.import_module('src.common.utils')
    monkeypatch.setattr(utils, 'generate_with_groq', _fake_generate_with_groq)
    fake_collection = Mock()
    fake_collection.insert_one = Mock(return_value=Mock())
    monkeypatch.setattr(utils, 'collection', fake_collection)

    # Act: call the async function (imported from the module we patched)
    generate_lesson_content = utils.generate_lesson_content

    user_id = "00000000-0000-0000-0000-000000000001"
    result = asyncio.run(generate_lesson_content(user_id=user_id, db_session=mock_db, lesson_title=None, num_of_lessons=1))

    # Assert: default profile was added and commit/refresh called
    assert mock_db.add.called, "Expected a default Profile to be added to the DB session"
    assert mock_db.commit.called, "Expected DB session commit to be called"
    assert mock_db.refresh.called, "Expected DB session refresh to be called"

    # Assert: lessons were returned and saved to Mongo
    assert 'lessons' in result and len(result['lessons']) == 1
    assert fake_collection.insert_one.called, "Expected lesson document to be inserted into Mongo"
