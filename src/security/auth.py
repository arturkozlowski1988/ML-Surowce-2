"""
Authentication and Authorization Module.
Provides user management, password hashing, and role-based access control.

Roles:
- admin: Full access (database change, connection wizard, user management)
- purchaser: Limited access (analysis, prediction, AI assistant - no db change)
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
from enum import Enum

logger = logging.getLogger('Auth')

# Try to import bcrypt, fall back to hashlib if not available
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    import hashlib
    BCRYPT_AVAILABLE = False
    logger.warning("bcrypt not installed, using less secure hashlib fallback")


class UserRole(str, Enum):
    """User roles with associated permissions."""
    ADMIN = "admin"
    PURCHASER = "purchaser"
    
    @property
    def can_change_database(self) -> bool:
        return self == UserRole.ADMIN
    
    @property
    def can_access_wizard(self) -> bool:
        return self == UserRole.ADMIN
    
    @property
    def can_manage_users(self) -> bool:
        return self == UserRole.ADMIN
    
    @property
    def display_name(self) -> str:
        names = {
            UserRole.ADMIN: "Administrator",
            UserRole.PURCHASER: "Zakupowiec"
        }
        return names.get(self, self.value)


@dataclass
class User:
    """User data model."""
    username: str
    role: str
    password_hash: str
    display_name: Optional[str] = None
    
    def get_role(self) -> UserRole:
        """Returns UserRole enum for this user."""
        try:
            return UserRole(self.role)
        except ValueError:
            return UserRole.PURCHASER  # Default to least privilege
    
    def can_change_database(self) -> bool:
        return self.get_role().can_change_database
    
    def can_access_wizard(self) -> bool:
        return self.get_role().can_access_wizard
    
    def can_manage_users(self) -> bool:
        return self.get_role().can_manage_users


class AuthManager:
    """Manages user authentication and authorization."""
    
    DEFAULT_USERS_FILE = "config/users.json"
    
    def __init__(self, users_file: str = None):
        """
        Initialize AuthManager.
        
        Args:
            users_file: Path to users JSON file. Defaults to config/users.json
        """
        if users_file is None:
            # Resolve relative to project root
            project_root = Path(__file__).parent.parent.parent
            self.users_file = project_root / self.DEFAULT_USERS_FILE
        else:
            self.users_file = Path(users_file)
        
        self._users: Dict[str, User] = {}
        self._load_users()
    
    def _ensure_config_dir(self):
        """Ensures config directory exists."""
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_users(self):
        """Loads users from JSON file."""
        self._users = {}
        
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_data in data.get('users', []):
                        user = User(**user_data)
                        self._users[user.username.lower()] = user
                logger.info(f"Loaded {len(self._users)} users from {self.users_file}")
            except Exception as e:
                logger.error(f"Error loading users: {e}")
        
        # Create default admin if no users exist
        if not self._users:
            self._create_default_admin()
    
    def _create_default_admin(self):
        """Creates default admin user if none exists."""
        logger.info("Creating default admin user")
        self.create_user(
            username="admin",
            password="admin123",
            role=UserRole.ADMIN,
            display_name="Administrator"
        )
    
    def _save_users(self):
        """Saves users to JSON file."""
        self._ensure_config_dir()
        
        try:
            data = {
                'users': [asdict(user) for user in self._users.values()]
            }
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self._users)} users to {self.users_file}")
        except Exception as e:
            logger.error(f"Error saving users: {e}")
            raise
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hashes password using bcrypt (or hashlib fallback).
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        if BCRYPT_AVAILABLE:
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        else:
            # Fallback to SHA256 (less secure, but works without bcrypt)
            return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verifies password against hash.
        
        Args:
            password: Plain text password to verify
            password_hash: Stored hash
            
        Returns:
            True if password matches
        """
        if BCRYPT_AVAILABLE:
            try:
                return bcrypt.checkpw(
                    password.encode('utf-8'), 
                    password_hash.encode('utf-8')
                )
            except Exception:
                return False
        else:
            # Fallback verification
            return hashlib.sha256(password.encode('utf-8')).hexdigest() == password_hash
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticates user with username and password.
        
        Args:
            username: User's username (case-insensitive)
            password: User's password
            
        Returns:
            User object if authenticated, None otherwise
        """
        username_lower = username.lower()
        user = self._users.get(username_lower)
        
        if user is None:
            logger.warning(f"Authentication failed: user '{username}' not found")
            return None
        
        if self.verify_password(password, user.password_hash):
            logger.info(f"User '{username}' authenticated successfully")
            return user
        else:
            logger.warning(f"Authentication failed: wrong password for '{username}'")
            return None
    
    def create_user(
        self, 
        username: str, 
        password: str, 
        role: UserRole,
        display_name: str = None
    ) -> bool:
        """
        Creates a new user.
        
        Args:
            username: Unique username
            password: Plain text password
            role: User role (UserRole enum)
            display_name: Optional display name
            
        Returns:
            True if created successfully, False if user exists
        """
        username_lower = username.lower()
        
        if username_lower in self._users:
            logger.warning(f"Cannot create user: '{username}' already exists")
            return False
        
        user = User(
            username=username,
            role=role.value,
            password_hash=self.hash_password(password),
            display_name=display_name or username
        )
        
        self._users[username_lower] = user
        self._save_users()
        logger.info(f"Created user '{username}' with role '{role.value}'")
        return True
    
    def delete_user(self, username: str) -> bool:
        """
        Deletes a user.
        
        Args:
            username: Username to delete
            
        Returns:
            True if deleted, False if not found
        """
        username_lower = username.lower()
        
        if username_lower not in self._users:
            return False
        
        # Prevent deleting last admin
        user = self._users[username_lower]
        if user.get_role() == UserRole.ADMIN:
            admin_count = sum(1 for u in self._users.values() if u.get_role() == UserRole.ADMIN)
            if admin_count <= 1:
                logger.warning("Cannot delete last admin user")
                return False
        
        del self._users[username_lower]
        self._save_users()
        logger.info(f"Deleted user '{username}'")
        return True
    
    def change_password(self, username: str, new_password: str) -> bool:
        """
        Changes user's password.
        
        Args:
            username: Username
            new_password: New plain text password
            
        Returns:
            True if changed successfully
        """
        username_lower = username.lower()
        
        if username_lower not in self._users:
            return False
        
        user = self._users[username_lower]
        user.password_hash = self.hash_password(new_password)
        self._save_users()
        logger.info(f"Password changed for user '{username}'")
        return True
    
    def get_all_users(self) -> List[User]:
        """Returns list of all users (without password hashes exposed)."""
        return list(self._users.values())
    
    def get_user(self, username: str) -> Optional[User]:
        """Gets user by username."""
        return self._users.get(username.lower())


# Singleton instance for app-wide use
_auth_manager: Optional[AuthManager] = None

def get_auth_manager() -> AuthManager:
    """Returns singleton AuthManager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
