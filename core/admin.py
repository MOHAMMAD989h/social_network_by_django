from django.contrib import admin

from core.models import Profile, Post, LikePost, FollowersCount, Comments, MyFavorite, RequestFollow, Conversation, \
    Message

admin.site.register(Profile)
admin.site.register(Post)
admin.site.register(LikePost)
admin.site.register(FollowersCount)
admin.site.register(RequestFollow)
admin.site.register(Message)
admin.site.register(Conversation)
admin.site.register(Comments)
admin.site.register(MyFavorite)