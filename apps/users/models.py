import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The email field is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None 

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField('email address', unique=True)
    first_name = models.CharField('first name', max_length=255, blank=True)
    last_name = models.CharField('last name', max_length=255, blank=True)

    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)

    # Tracking fields
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = []

    objects = CustomUserManager()
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.email
    
    @property
    def role(self):
        if self.groups.filter(name='Admin').exists():
            return 'Admin'
        return 'Fan'

class FanProfile(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('it', 'Italian'),
        ('pt', 'Portuguese'),
        ('tr', 'Turkish'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='fan_profile')

    # Favorites
    favorite_teams = models.ManyToManyField('sports.Team', blank=True, related_name='favorited_by_fans')
    favorite_leagues = models.ManyToManyField('sports.League', blank=True, related_name='favorited_by_fans')
    favorite_fixtures = models.ManyToManyField('sports.Fixture', blank=True, related_name='favorited_by_fans')

    # Notification Preferences
    receive_live_notifications = models.BooleanField(default=True)
    receive_news_updates = models.BooleanField(default=True)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    
    # Tracks the timestamp when the user last opened the inbox
    last_inbox_check = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fan: {self.user.email}"
    

class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    can_manage_news = models.BooleanField(default=True)
    can_manage_users = models.BooleanField(default=True)

    def __str__(self):
        return f"Admin: {self.user.email}"

class OneTimePassword(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.otp}"
    
class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.timestamp}"

class GuestFavorite(models.Model):
    device_id = models.CharField(max_length=255, unique=True, db_index=True)
    favorite_teams = models.ManyToManyField('sports.Team', blank=True, related_name='guest_favorites')
    favorite_leagues = models.ManyToManyField('sports.League', blank=True, related_name='guest_favorites')
    favorite_fixtures = models.ManyToManyField('sports.Fixture', blank=True, related_name='guest_favorites')
    last_inbox_check = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Guest: {self.device_id}"