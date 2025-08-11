#!/usr/bin/env python3
"""
Database management script for ByteCorp project.
Provides commands for database migrations and setup.
"""
import os
import sys
from flask.cli import FlaskGroup
from migrations import app, db, migrate

cli = FlaskGroup(app)

@cli.command("init-db")
def init_db():
    """Initialize the database with all tables."""
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully!")

@cli.command("create-migration")
def create_migration():
    """Create a new migration file."""
    os.system("flask db migrate -m 'Initial migration'")
    print("✅ Migration file created!")

@cli.command("upgrade-db")
def upgrade_db():
    """Apply all pending migrations."""
    os.system("flask db upgrade")
    print("✅ Database upgraded successfully!")

@cli.command("downgrade-db")
def downgrade_db():
    """Rollback the last migration."""
    os.system("flask db downgrade")
    print("✅ Database downgraded successfully!")

@cli.command("reset-db")
def reset_db():
    """Drop all tables and recreate them."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✅ Database reset successfully!")

if __name__ == '__main__':
    cli()
