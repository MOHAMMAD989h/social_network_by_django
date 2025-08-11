import uuid
from datetime import datetime
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    id_user = models.IntegerField()
    bio = models.TextField(blank=True)
    email_confirmed = models.BooleanField(default=False)
    phone_confirmed = models.BooleanField(default=False)
    phone_number = models.TextField(blank=True)
    private_public = models.BooleanField(default=False)
    profileimg = models.ImageField(upload_to='profile_images',default='blank-profile-picture.png')
    profilebackground = models.ImageField(upload_to='profile_images',default='blank-profile-picture.png')
    location = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.username

class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.CharField(max_length=100)
    image = models.FileField(upload_to='post_images',default='blank-post-picture.png')
    caption = models.TextField()
    created_at = models.DateTimeField(default=datetime.now)
    no_of_likes = models.IntegerField(default=0)

    def __str__(self):
        return self.user

class LikePost(models.Model):
    post_id = models.CharField(max_length=500)
    username = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return self.username


class FollowersCount(models.Model):
    follower = models.CharField(max_length=100)
    user = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return self.user

class Comments(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField(max_length=500)
    created_at = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return self.user.username

class MyFavorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return self.user.username