import random
from django.utils import timezone
from datetime import timedelta
from itertools import chain

from django.contrib import messages, auth
from django.contrib.auth import user_logged_in
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect

from core.models import User, Profile, Post, LikePost, FollowersCount,Comments


@login_required(login_url='signin')
def index(request):
    user_object = User.objects.get(username=request.user.username)

    try:
        user_profile = Profile.objects.get(user=user_object)
    except Profile.DoesNotExist:
        return redirect('signin')

    user_following_list = []
    feed = []

    user_following = FollowersCount.objects.filter(follower=request.user.username)


    for users in user_following:
        user_following_list.append(users.user)

    for usernames in user_following_list:
        feed_lists = Post.objects.filter(user=usernames).prefetch_related('comments__user__profile')
        feed.append(feed_lists)

    feed_list = list(chain(*feed))


    following_with_profiles = []
    for follow in user_following:
        try:
            profile = Profile.objects.get(user__username=follow.user)

            time_diff = timezone.now() - follow.created_at

            total_minutes = int(time_diff.total_seconds() // 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60

            if hours > 0:
                time_ago_str = f"{hours} ساعت و {minutes} دقیقه پیش"
            else:
                time_ago_str = f"{minutes} دقیقه پیش"

            following_with_profiles.append({
                'username': follow.user,
                'profileimg': profile.profileimg.url,
                'created_at': time_ago_str,
            })
        except Profile.DoesNotExist:
            continue

    # posts = Post.objects.all()

    all_users = User.objects.all()
    user_following_all = []

    for user in user_following:
        user_list = User.objects.get(username=user.user)
        user_following_all.append(user_list)

    new_suggestion_list = [x for x in list(all_users) if(x not in list(user_following_all))]
    current_user = User.objects.filter(username=request.user.username)
    final_suggestion_list = [x for x in list(new_suggestion_list) if  (x not in list(current_user)) ]
    random.shuffle(final_suggestion_list)

    username_profile = []
    username_profile_list = []

    for users in final_suggestion_list:
        username_profile.append(users.id)

    for ids in username_profile:
        profile_lists = Profile.objects.filter(id_user=ids)
        username_profile_list.append(profile_lists)

    suggestions_username_profile_list = list(chain(*username_profile_list))

    return render(request, 'index.html', {'user_profile': user_profile,'following_notifications':following_with_profiles,'posts': feed_list,'suggestions_username_profile_list':suggestions_username_profile_list[:4]})


def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2']

        if password == password2:
            if User.objects.filter(email=email).exists():
                messages.info(request, 'Email already registered')
                return redirect('signup')
            elif User.objects.filter(username=username).exists():
                messages.info(request, 'Username already registered')
                return redirect('signup')
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()

                user_login = auth.authenticate(username=username, password=password)
                auth.login(request, user_login)

                user_model = User.objects.get(username=username)
                new_profile = Profile.objects.create(user=user_model,id_user=user_model.id)
                new_profile.save()

                return redirect('settings')
        else:
            messages.info(request, 'Passwords do not match')
            return redirect('signup')


    else:
        return render(request, 'signup.html')


def signin(request):
    if request.method == 'POST':

        username = request.POST['username']
        password = request.POST['password']

        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)
            return redirect('/')
        else:
            messages.info(request, 'user is not valid')
            return redirect('signin')

    else:
        return render(request, 'signin.html')

@login_required(login_url='signin')
def logout(request):
    auth.logout(request)
    return redirect('signin')

@login_required(login_url='signin')
def settings(request):
    user_profile = Profile.objects.get(user=request.user)

    if request.method == 'POST':

        if request.FILES.get('image') is None:
            image = user_profile.profileimg
            bio = request.POST['bio']
            location = request.POST['location']

            user_profile.profileimg = image
            user_profile.bio = bio
            user_profile.location = location

            user_profile.save()

        if request.FILES.get('image') is not None:
            image = request.FILES.get('image')
            bio = request.POST['bio']
            location = request.POST['location']

            user_profile.profileimg = image
            user_profile.bio = bio
            user_profile.location = location

            user_profile.save()
        return redirect('settings')
    return render(request, 'setting.html',{'user_profile':user_profile})

@login_required(login_url='signin')
def upload(request):

    if request.method == 'POST':
        user = request.user.username
        image = request.FILES.get('image_upload')
        caption = request.POST['caption']

        new_post = Post.objects.create(caption=caption,user=user,image=image)
        new_post.save()

        return redirect('/')
    else:
        return redirect('upload')

@login_required(login_url='signin')
def like_post(request):
    username = request.user.username
    post_id = request.GET.get('post_id')

    post = Post.objects.get(id=post_id)

    like_filter = LikePost.objects.filter(post_id=post_id, username=username).first()
    if like_filter is None:
        new_like = LikePost.objects.create(post_id=post_id, username=username)
        new_like.save()

        post.no_of_likes += 1
        post.save()

        return redirect(request.META['HTTP_REFERER'])
    else:
        like_filter.delete()

        post.no_of_likes -= 1
        post.save()
        
        return redirect(request.META['HTTP_REFERER'])

@login_required(login_url='signin')
def profile(request, pk):

    user_object = User.objects.get(username=pk)
    user_profile = Profile.objects.get(user=user_object)
    user_posts = Post.objects.filter(user=pk)
    user_post_length = len(user_posts)

    follower = request.user.username
    user = pk

    if FollowersCount.objects.filter(follower=follower, user=user).first():
        button_text = 'Unfollow'
    else:
        button_text = 'Follow'

    user_followers = len(FollowersCount.objects.filter(user=pk))
    user_following = len(FollowersCount.objects.filter(follower=pk))

    context = {
        'user_object': user_object,
        'user_profile': user_profile,
        'user_posts': user_posts,
        'user_post_length': user_post_length,
        'button_text': button_text,
        'user_followers': user_followers,
        'user_following': user_following,
    }
    return render(request,'profile.html', context)

@login_required(login_url='signin')
def follow(request):
    if request.method == 'POST':
        follower = request.POST['follower']
        user = request.POST['user']

        if FollowersCount.objects.filter(user=user, follower=follower).first():
            delete_follower = FollowersCount.objects.get(user=user, follower=follower)
            delete_follower.delete()
            return redirect('/profile/'+ user)
        else:
            new_follower = FollowersCount.objects.create(user=user, follower=follower)
            new_follower.save()
            return redirect('/profile/'+ user)
    else:
        return redirect('/')

@login_required(login_url='signin')
def search(request):
    user_object = User.objects.get(username=request.user.username)
    user_profile = Profile.objects.get(user=user_object)

    if request.method == 'POST':
        user_object = User.objects.get(username=request.user.username)
        user_profile = Profile.objects.get(user=user_object)

        if request.method == 'POST':
            username = request.POST['username']
            username_object = User.objects.filter(username__icontains=username)

            username_profile = []
            username_profile_list = []

            for users in username_object:
                username_profile.append(users.id)

            for ids in username_profile:
                profile_lists = Profile.objects.filter(id_user=ids)
                username_profile_list.append(profile_lists)

            username_profile_list = list(chain(*username_profile_list))

    return render(request, 'search.html',{'user_profile': user_profile,'username_profile_list':username_profile_list})

@login_required
def delete_post(request):
    if request.method == 'POST':
        post_id = request.POST.get('post_id')
        post = Post.objects.get(id=post_id)
        if post.user == request.user.username:
            post.delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def explore(request):
    user_object = User.objects.get(username=request.user.username)
    user_profile = Profile.objects.get(user=user_object)
    posts = Post.objects.all().order_by('-created_at')
    return render(request, 'explore.html', {'user_profile': user_profile,'posts': posts})

@login_required
def comment(request, post_id):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            post = Post.objects.get(id=post_id)
            comment_text = request.POST.get('comment_text')
            if len(comment_text) < 500:
                new_comment = Comments.objects.create(
                    post=post,
                    user=request.user,
                    comment=comment_text
                    )
                new_comment.save()
            return redirect(request.META.get('HTTP_REFERER', '/'))

        except Post.DoesNotExist:
            return redirect('/')

    return redirect('/')

@login_required
def commentDelete(request, post_id):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            post = Post.objects.get(id=post_id)
            comment_text = request.POST.get('comment_txt')
            user = request.user
            comment = Comments.objects.filter(post=post, user=user, comment=comment_text)
            comment.delete()
            return redirect(request.META.get('HTTP_REFERER', '/'))
        except Post.DoesNotExist:
            return redirect('/')

    return redirect('/')
