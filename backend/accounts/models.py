from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from .managers import UserManager

#creating the user class

class User(AbstractBaseUser):
    user_id = models.CharField(
        max_length= 20,
        primary_key= True)

    first_name = models.CharField(
        max_length= 100
    )

    last_name = models.CharField(
        max_length= 100
    )

    email = models.EmailField(
        max_length= 255,
        unique = True
    )

    account_status = models.CharField(
        max_length= 20,
        default = "active"
    )

    is_active = models.BooleanField(
        default= True
    )

    is_staff = models.BooleanField(
        default= False
    )

    created_at = models.DateTimeField(
        auto_now_add= True
    )

    updated_at = models.DateTimeField(
        auto_now= True
    )

    objects = UserManager()

    USERNAME_FIELD = "email"

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email

    
class UserProfile(models.Model):
    profile_id = models.CharField(
        max_length = 20,
        primary_key = True
    )

    user = models.OneToOneField(
        User,
        on_delete= models.PROTECT,
        related_name= "profile",
        db_column= "user_id"
    )

    date_of_birth = models.DateField()

    age_group = models.CharField(
        max_length = 20,
        blank = True, #it indicates to django that the user can leave this empty
        null = True #it indicates the database can store null
    )

    sex = models.CharField(
        max_length = 20,
        blank= True,
        null= True
    )

    country = models.CharField(
        max_length= 100,
        blank= True,
        null = True
    )

    state_or_region = models.CharField(
        max_length= 100,
        blank= True,
        null= True
    )

    profile_status = models.CharField(
        max_length= 20
    )

    created_at = models.DateTimeField()

    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "user_profiles"

    def __str__(self):
        return f"{self.user_id} - {self.profile_status}"


class ProductEnrollment(models.Model):
    enrollment_id = models.CharField(
        max_length= 20,
        primary_key= True
    )

    user = models.ForeignKey(
        User,
        on_delete= models.PROTECT,
        related_name= "product_enrollments",
        db_column= "user_id"
    )

    product_code = models.CharField(
        max_length= 30
    )

    enrollment_status = models.CharField(
        max_length= 20
    )

    enrolled_at = models.DateTimeField()

    discontinued_at = models.DateTimeField(
        blank = True,
        null = True
    )

    class Meta:
        managed = False
        db_table = "product_enrollments"
        constraints = [
            models.UniqueConstraint(
                fields = ["user", "product_code"],
                name = "unique_user_product_enrollment"
            )
        ]

    def __str__(self):
        return f"{self.user_id} - {self.product_code}"