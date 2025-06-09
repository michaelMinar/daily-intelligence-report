"""Database initialization utility for the daily intelligence report system."""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Optional

try:
    from importlib.metadata import distribution
    from importlib.resources import files
except ImportError:
    # Python < 3.9 fallback
    from importlib_resources import files
    try:
        from importlib_metadata import distribution
    except ImportError:
        distribution = None

from .utils.log import get_logger

logger = get_logger(__name__)

DEFAULT_DB_PATH = "./data/dev/intel.db"

def get_schema_path() -> Path:
    """Get schema file path for both development and installed packages."""
    # Try to use importlib.resources for installed packages
    try:
        # Get package names using more reliable methods
        package_names = []
        
        # Method 1: Use __package__ if available and not running as __main__
        if __package__ and __package__ != '__main__':
            # Get top-level package from __package__
            top_package = __package__.split('.')[0]
            package_names.append(top_package)
        
        # Method 2: Try to get package name from distribution metadata
        if distribution is not None:
            try:
                # Common package names to try
                dist_names = ['daily-intelligence-report', 'intel']
                for dist_name in dist_names:
                    try:
                        dist = distribution(dist_name)
                        # Use the distribution name or top-level packages
                        package_names.append(dist.metadata['Name'].replace('-', '_'))
                        if hasattr(dist, 'files') and dist.files:
                            # Get actual package names from installed files
                            for file in dist.files:
                                if file.suffix == '.py' and '/' in str(file):
                                    pkg_name = str(file).split('/')[0]
                                    if pkg_name not in package_names:
                                        package_names.append(pkg_name)
                                    break
                    except Exception:
                        continue
            except Exception:
                pass
        
        # Method 3: Fallback to common names
        fallback_names = ['intel', 'daily_intelligence_report', 'src']
        for name in fallback_names:
            if name not in package_names:
                package_names.append(name)
        
        # Try each package name
        for package_name in package_names:
            try:
                schema_files = files(package_name).joinpath('infra')
                schema_path = schema_files / 'schema.sql'
                if schema_path.is_file():
                    return Path(str(schema_path))
            except (
                ImportError,
                AttributeError,
                FileNotFoundError,
                ModuleNotFoundError,
            ):
                continue
    except Exception:
        pass
    
    # Fallback to relative path for development
    schema_path = Path(__file__).parent.parent.parent / "infra" / "schema.sql"
    if schema_path.exists():
        return schema_path
    
    raise FileNotFoundError("Could not locate schema.sql file")


def get_schema_version(db_path: Path) -> int:
    """Get the current schema version from the database.
    
    Args:
        db_path: Path to the SQLite database
        
    Returns:
        Current schema version, 0 if database doesn't exist
    """
    if not db_path.exists():
        return 0
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("PRAGMA user_version")
            return cursor.fetchone()[0]
    except sqlite3.Error as e:
        logger.error(f"Failed to get schema version: {e}")
        return 0


def initialize_database(db_path: Optional[str] = None) -> bool:
    """Initialize the SQLite database with the schema.
    
    Args:
        db_path: Path to the database file, uses default if None
        
    Returns:
        True if initialization succeeded, False otherwise
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    db_file = Path(db_path)
    
    # Create parent directories if they don't exist
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Initializing database at: {db_file}")
    
    # Get schema file path
    try:
        schema_path = get_schema_path()
    except FileNotFoundError as e:
        logger.error(f"Schema file not found: {e}")
        return False
    
    try:
        # Read schema SQL
        schema_sql = schema_path.read_text(encoding="utf-8")
        
        # Get current version
        current_version = get_schema_version(db_file)
        logger.info(f"Current schema version: {current_version}")
        
        # Connect and execute schema
        with sqlite3.connect(db_file) as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Execute schema SQL
            conn.executescript(schema_sql)
            
            # Set schema version to 1 for initial schema
            conn.execute("PRAGMA user_version = 1")
            
            # Verify the schema was applied
            new_version = conn.execute("PRAGMA user_version").fetchone()[0]
            
            if new_version > current_version:
                logger.info(f"Schema updated to version {new_version}")
            elif current_version == 0:
                logger.info(f"Database initialized with schema version {new_version}")
            else:
                logger.info("Database schema is up to date")
            
            # Verify tables were created
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [table[0] for table in tables]
            
            expected_tables = [
                "sources", "posts", "embeddings", "clusters", "post_clusters"
            ]
            missing_tables = [t for t in expected_tables if t not in table_names]
            
            if missing_tables:
                logger.error(f"Missing tables after initialization: {missing_tables}")
                return False
            
            logger.info(f"Successfully created tables: {', '.join(expected_tables)}")
            return True
            
    except sqlite3.Error as e:
        logger.error(f"Database initialization failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during initialization: {e}")
        return False


def main() -> int:
    """CLI entry point for database initialization."""
    parser = argparse.ArgumentParser(
        description="Initialize the daily intelligence report database"
    )
    parser.add_argument(
        "--db-path",
        help=f"Path to database file (default: {DEFAULT_DB_PATH})",
        default=None,
    )
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (use -vv for debug level)",
    )
    
    args = parser.parse_args()
    
    # Adjust logging level based on verbosity
    if args.verbose >= 2:
        logging_level = "DEBUG"
    elif args.verbose >= 1:
        logging_level = "INFO"
    else:
        logging_level = "WARNING"
    
    # Set the logging level for this module
    logger.setLevel(getattr(logging, logging_level))
    
    # Initialize database
    success = initialize_database(args.db_path)
    
    if success:
        logger.info("Database initialization completed successfully")
        return 0
    else:
        logger.error("Database initialization failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())