from django.urls import include, path

from . import views

urlpatterns = [
    path('',views.index,name='index'),
    path('settings',views.settings,name='settings'),
    path('upload', views.upload, name='uplaod'),
    path('follow', views.follow, name='follow'),
    path('search', views.search, name='search'),
    path('profile/<str:pk>', views.profile, name='profile'),
    path('like-post', views.like_post, name='like-post'),
    path('signup', views.signup, name='signup'),
    path('signin', views.signin, name='signin'),
    path('logout', views.signin, name='logout'),
    path('delete-post/', views.delete_post, name='delete_post'),
    path('explore/', views.explore, name='explore'),
    path('comment/<str:post_id>', views.comment, name='comment'),
    path('comment/delete/<str:post_id>', views.commentDelete, name='comment_delete'),
]