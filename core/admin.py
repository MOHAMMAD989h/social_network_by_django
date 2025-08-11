from django.contrib import admin

from core.models import Profile, Post, LikePost, FollowersCount, Comments, MyFavorite

admin.site.register(Profile)
admin.site.register(Post)
admin.site.register(LikePost)
admin.site.register(FollowersCount)
admin.site.register(Comments)
admin.site.register(MyFavorite)