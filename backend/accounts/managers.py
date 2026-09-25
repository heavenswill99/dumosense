from django.contrib.auth.base_user import BaseUserManager
#Base manager for custom users

# Custom manager for user creation
class UserManager(BaseUserManager):
    """Custom user manager."""

    # Create and save for user creation
    def create_user(
        self,
        email,
        password = None,
        **extra_fields
    ):
        # ensuring email is provided
        if not email:
            raise ValueError ("Users must have an email address.")

        #Normalize email format
        email = self.normalize_email(email)

        #creating user instance
        user = self.model(
            email = email,
            **extra_fields
        )

        #hashing and setting password
        user.set_password(password)
        user.save(using = self._db) #saving user to database

        return user

    def create_superuser(
            self, email, password = None, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("account_status", "active")

        return self.create_user(
            email = email,
            password = password,
            **extra_fields
        )
    