#!/usr/bin/env bash
python - << 'EOF'
from app.db.base import SessionLocal
from app.core.achievements.models import AchievementRule

rules = [
    ('first_event', 'Первое событие', 'https://example.com/icons/first_event.png', 'Награда за первое событие'),
]

db = SessionLocal()
for code, title, icon_url, desc in rules:
    if not db.query(AchievementRule).filter_by(code=code).first():
        db.add(AchievementRule(
            code=code,
            title=title,
            icon_url=icon_url,
            description=desc,
        ))
db.commit()
EOF
