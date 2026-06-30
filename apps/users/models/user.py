import uuid
from django.db import models
from core.models import BaseModel
from django.contrib.auth.models import AbstractUser, BaseUserManager
from phonenumber_field.modelfields import PhoneNumberField

class UserManager(BaseUserManager):
    use_in_migrations = True
    
    def _create_user(self, email, password, **extra_fields):
        # Create and save a User with the given email and password.
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        
        # Auto-generate unique username if not provided
        if not extra_fields.get("username"):
            username = email.split('@')[0]
            if self.model.objects.filter(username=username).exists():
                username = f"{username}_{uuid.uuid4().hex[:8]}"
            extra_fields["username"] = username
            
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)
    
    def create_superuser(self, email, password=None, **extra_fields):
        # Create and save a SuperUser with the given email and password.
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
            
        return self._create_user(email, password, **extra_fields)
        
    def get_by_natural_key(self, email):
        # For user ID (email) case insensitive
        case_insensitive_username_field = "{}__iexact".format(self.model.USERNAME_FIELD)
        return self.get(**{case_insensitive_username_field: email})

class User(BaseModel, AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("others", "Others")
    ]
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("seller", "Seller"),
        ("customer", "Customer")
    ]
    
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = PhoneNumberField(null=True, blank=True)
    gender = models.CharField(max_length=15, choices=GENDER_CHOICES, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")
    is_email_verified = models.BooleanField(default=False)

    objects = UserManager()

    def __str__(self):
        return self.get_full_name()
    
    def get_full_name(self):
        if self.full_name:
            return self.full_name
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.username or self.email.split("@")[0]
        
class UserProfile(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        blank=True, null=True
    )
    bio = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.get_full_name()}'s Profile"