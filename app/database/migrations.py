"""
Database migration system for Agent Hub
"""
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import re

from ..logging import get_logger
from .connection import Database

logger = get_logger(__name__)


class Migration:
    """Represents a single database migration"""
    
    def __init__(self, version: int, description: str, sql_content: str, filepath: Path):
        self.version = version
        self.description = description
        self.sql_content = sql_content
        self.filepath = filepath
    
    def __repr__(self) -> str:
        return f"Migration(version={self.version}, description='{self.description}')"
    
    def __lt__(self, other: 'Migration') -> bool:
        return self.version < other.version


class MigrationManager:
    """Manages database schema migrations"""
    
    def __init__(self, database: Database, migrations_dir: Optional[Path] = None):
        self.database = database
        self.migrations_dir = migrations_dir or Path(__file__).parent.parent.parent / "database" / "migrations"
        
        logger.info("migration_manager_initialized", migrations_dir=str(self.migrations_dir))
    
    def _ensure_migrations_table(self) -> None:
        """Ensure the schema_migrations table exists"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT NOT NULL
        )
        """
        self.database.execute(create_table_sql)
        logger.debug("migrations_table_ensured")
    
    def get_applied_migrations(self) -> List[int]:
        """Get list of applied migration versions"""
        self._ensure_migrations_table()
        
        rows = self.database.fetch_all("SELECT version FROM schema_migrations ORDER BY version")
        versions = [row["version"] for row in rows]
        
        logger.debug("applied_migrations_retrieved", count=len(versions), versions=versions)
        return versions
    
    def get_current_version(self) -> int:
        """Get current database schema version"""
        applied = self.get_applied_migrations()
        return max(applied) if applied else 0
    
    def discover_migrations(self) -> List[Migration]:
        """Discover all migration files in the migrations directory"""
        migrations = []
        
        if not self.migrations_dir.exists():
            logger.warning("migrations_directory_not_found", path=str(self.migrations_dir))
            return migrations
        
        # Pattern to match migration files: 001_initial.sql, 002_add_indexes.sql, etc.
        pattern = re.compile(r'^(\d{3})_(.+)\.sql$')
        
        for file_path in self.migrations_dir.glob("*.sql"):
            match = pattern.match(file_path.name)
            if match:
                version = int(match.group(1))
                description = match.group(2).replace('_', ' ').title()
                
                try:
                    sql_content = file_path.read_text(encoding='utf-8')
                    migration = Migration(version, description, sql_content, file_path)
                    migrations.append(migration)
                    
                    logger.debug("migration_discovered", 
                               version=version, 
                               description=description,
                               file=file_path.name)
                
                except Exception as e:
                    logger.error("migration_read_failed", 
                               file=file_path.name, 
                               error=str(e))
            else:
                logger.warning("migration_filename_invalid", file=file_path.name)
        
        # Sort by version
        migrations.sort()
        
        logger.info("migrations_discovered", count=len(migrations))
        return migrations
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations"""
        applied_versions = set(self.get_applied_migrations())
        all_migrations = self.discover_migrations()
        
        pending = [m for m in all_migrations if m.version not in applied_versions]
        
        logger.info("pending_migrations_identified", count=len(pending))
        return pending
    
    def apply_migration(self, migration: Migration) -> None:
        """Apply a single migration"""
        logger.info("migration_applying", 
                   version=migration.version, 
                   description=migration.description)
        
        try:
            with self.database.transaction() as conn:
                # Execute migration SQL
                conn.executescript(migration.sql_content)
                
                # Record migration as applied
                conn.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                    (migration.version, migration.description)
                )
            
            logger.info("migration_applied_successfully", 
                       version=migration.version,
                       description=migration.description)
        
        except Exception as e:
            logger.error("migration_apply_failed", 
                        version=migration.version,
                        description=migration.description,
                        error=str(e))
            raise
    
    def rollback_migration(self, version: int) -> None:
        """Rollback a migration (removes from tracking, but doesn't undo changes)"""
        logger.warning("migration_rollback_requested", version=version)
        
        try:
            self.database.execute(
                "DELETE FROM schema_migrations WHERE version = ?",
                {"version": version}
            )
            
            logger.warning("migration_rollback_completed", version=version)
        
        except Exception as e:
            logger.error("migration_rollback_failed", version=version, error=str(e))
            raise
    
    def migrate_to_latest(self) -> int:
        """Apply all pending migrations"""
        logger.info("migration_to_latest_started")
        
        pending_migrations = self.get_pending_migrations()
        
        if not pending_migrations:
            current_version = self.get_current_version()
            logger.info("no_pending_migrations", current_version=current_version)
            return current_version
        
        applied_count = 0
        
        for migration in pending_migrations:
            try:
                self.apply_migration(migration)
                applied_count += 1
            except Exception as e:
                logger.error("migration_sequence_failed", 
                           failed_at_version=migration.version,
                           applied_count=applied_count,
                           error=str(e))
                raise
        
        final_version = self.get_current_version()
        logger.info("migration_to_latest_completed", 
                   applied_count=applied_count,
                   final_version=final_version)
        
        return final_version
    
    def migrate_to_version(self, target_version: int) -> None:
        """Migrate to a specific version"""
        current_version = self.get_current_version()
        
        if current_version == target_version:
            logger.info("already_at_target_version", version=target_version)
            return
        
        if current_version > target_version:
            logger.error("downgrade_not_supported", 
                        current_version=current_version,
                        target_version=target_version)
            raise ValueError("Database downgrade is not supported")
        
        logger.info("migration_to_version_started", 
                   current_version=current_version,
                   target_version=target_version)
        
        pending_migrations = self.get_pending_migrations()
        migrations_to_apply = [m for m in pending_migrations if m.version <= target_version]
        
        for migration in migrations_to_apply:
            self.apply_migration(migration)
        
        logger.info("migration_to_version_completed", target_version=target_version)
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get detailed migration status"""
        current_version = self.get_current_version()
        applied_migrations = self.get_applied_migrations()
        all_migrations = self.discover_migrations()
        pending_migrations = self.get_pending_migrations()
        
        status = {
            "current_version": current_version,
            "applied_count": len(applied_migrations),
            "pending_count": len(pending_migrations),
            "total_migrations": len(all_migrations),
            "applied_versions": applied_migrations,
            "pending_versions": [m.version for m in pending_migrations],
            "is_up_to_date": len(pending_migrations) == 0
        }
        
        logger.debug("migration_status_retrieved", **status)
        return status
    
    def validate_migrations(self) -> List[str]:
        """Validate migration files for common issues"""
        issues = []
        migrations = self.discover_migrations()
        
        if not migrations:
            issues.append("No migration files found")
            return issues
        
        # Check for version gaps
        versions = sorted([m.version for m in migrations])
        for i, version in enumerate(versions):
            expected_version = i + 1
            if version != expected_version:
                issues.append(f"Version gap detected: expected {expected_version}, found {version}")
        
        # Check for duplicate versions
        if len(versions) != len(set(versions)):
            issues.append("Duplicate migration versions detected")
        
        # Check file contents
        for migration in migrations:
            if not migration.sql_content.strip():
                issues.append(f"Migration {migration.version} is empty")
            
            if "DROP TABLE" in migration.sql_content.upper():
                issues.append(f"Migration {migration.version} contains DROP TABLE (potentially destructive)")
        
        if issues:
            logger.warning("migration_validation_issues", issues=issues)
        else:
            logger.info("migration_validation_passed")
        
        return issues


def run_migrations(database: Optional[Database] = None, migrations_dir: Optional[Path] = None) -> int:
    """Convenience function to run migrations"""
    from .connection import get_database
    
    if database is None:
        database = get_database()
    
    manager = MigrationManager(database, migrations_dir)
    return manager.migrate_to_latest()


def get_migration_status(database: Optional[Database] = None) -> Dict[str, Any]:
    """Convenience function to get migration status"""
    from .connection import get_database
    
    if database is None:
        database = get_database()
    
    manager = MigrationManager(database)
    return manager.get_migration_status()