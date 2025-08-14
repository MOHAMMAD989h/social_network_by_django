import http
import random
import re
from urllib.parse import quote

from django.utils import timezone
from datetime import timedelta, datetime
from itertools import chain

from django.views.decorators.http import require_POST
from user_agents import parse
from django.contrib import messages, auth
from django.contrib.auth import user_logged_in
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib.sessions.models import Session
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.contrib.auth.hashers import check_password

from core.models import User, Profile, Post, LikePost, FollowersCount, Comments, MyFavorite, RequestFollow, \
    Conversation, Message


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
            if hours < 24:
                following_with_profiles.append({
                    'username': follow.user,
                    'profileimg': profile.profileimg.url,
                    'created_at': time_ago_str,
                })
        except Profile.DoesNotExist:
            continue

    user_requests = RequestFollow.objects.filter(user=request.user)
    request_with_profiles = []
    for req in user_requests:
        try:
            profile = Profile.objects.get(user__username=req.follower)

            time_diff = timezone.now() - req.created_at

            total_minutes = int(time_diff.total_seconds() // 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60

            if hours > 0:
                time_ago_str = f"{hours} ساعت و {minutes} دقیقه پیش"
            else:
                time_ago_str = f"{minutes} دقیقه پیش"

            request_with_profiles.append({
                'username': req.follower,
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

    return render(request, 'index.html', {'user_profile': user_profile,'following_notifications':following_with_profiles,'request_notifications':request_with_profiles,'posts': feed_list,'suggestions_username_profile_list':suggestions_username_profile_list[:4]})


def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2']

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if password == password2:
            if User.objects.filter(email=email).exists():
                messages.info(request, 'Email already registered')
                return redirect('signup')
            elif User.objects.filter(username=username).exists():
                messages.info(request, 'Username already registered')
                return redirect('signup')
            elif User.objects.filter(password=password).exists():
                messages.info(request, 'Password already registered')
                return redirect('signup')
            elif len(username) < 3:
                messages.info(request, 'Username too short')
                return redirect('signup')
            #elif re.match(email_pattern, email) :
            elif len(email) < 3:
                messages.info(request, 'Email not valid')
                return redirect('signup')
            elif len(password) < 8:
                messages.info(request, 'Password must be at least 8 characters')
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

            ua_string = request.META.get('HTTP_USER_AGENT', '')
            user_agent = parse(ua_string)

            request.session['user_agent'] = {
                'os_family': user_agent.os.family,
                'browser_family': user_agent.browser.family,
                'device_type': user_agent.device.family
            }

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
    user_sessions = []

    all_sessions = Session.objects.filter(expire_date__gte=timezone.now())
    for session in all_sessions:
        session_data = session.get_decoded()
        if session_data.get('_auth_user_id') == str(request.user.id):
            ua_info = session_data.get('user_agent', {})
            session.ua_info = ua_info
            user_sessions.append(session)

    if request.method == 'POST':

        if request.FILES.get('image') is None:
            if request.FILES.get('back_image') is None:
                image = user_profile.profileimg
                bio = request.POST['bio']
                location = request.POST['location']
                back_image = user_profile.profilebackground

                user_profile.profileimg = image
                user_profile.bio = bio
                user_profile.location = location
                user_profile.profilebackground = back_image

                user_profile.save()
            if request.FILES.get('back_image') is not None:
                image = user_profile.profileimg
                bio = request.POST['bio']
                location = request.POST['location']
                back_image = request.FILES['back_image']

                user_profile.profileimg = image
                user_profile.bio = bio
                user_profile.location = location
                user_profile.profilebackground = back_image

                user_profile.save()


        if request.FILES.get('image') is not None:
            if request.FILES.get('back_image') is None:
                image = request.FILES.get('image')
                bio = request.POST['bio']
                location = request.POST['location']
                back_image = user_profile.profilebackground

                user_profile.profileimg = image
                user_profile.bio = bio
                user_profile.location = location
                user_profile.profilebackground = back_image

            if request.FILES.get('back_image') is not None:
                image = request.FILES.get('image')
                bio = request.POST['bio']
                location = request.POST['location']
                back_image = request.FILES['back_image']

                user_profile.profileimg = image
                user_profile.bio = bio
                user_profile.location = location
                user_profile.profilebackground = back_image

                user_profile.save()
        return redirect('settings')
    return render(request, 'setting.html',{'user_profile':user_profile,'sessions': user_sessions})

@login_required(login_url='signin')
def upload(request):
    if request.method == 'POST':
        user = request.user.username
        image = request.FILES.get('image_upload')
        if image is None:
            return redirect('/')
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
    elif RequestFollow.objects.filter(follower=follower, user=user).first():
        button_text = 'SendRequest'
    else:
        button_text = 'Follow'

    user_followers = len(FollowersCount.objects.filter(user=pk))
    user_following = len(FollowersCount.objects.filter(follower=pk))
    user_follow = FollowersCount.objects.filter(user=user_object.username, follower=request.user.username)

    private_public = True

    if  user_profile.private_public or not user_follow.exists():
        private_public = False

    context = {
        'user_object': user_object,
        'user_profile': user_profile,
        'user_posts': user_posts,
        'user_post_length': user_post_length,
        'button_text': button_text,
        'user_followers': user_followers,
        'user_following': user_following,
        'private_public': private_public,
    }
    return render(request,'profile.html', context)

@login_required(login_url='signin')
def follow(request):
    if request.method == 'POST':
        follower = request.POST['follower']
        user = request.POST['user']
        user_object = User.objects.get(username=user)
        is_private = Profile.objects.get(user=user_object).private_public  # True = Private

        if FollowersCount.objects.filter(user=user, follower=follower).exists():
            FollowersCount.objects.filter(user=user, follower=follower).delete()
            return redirect('/profile/' + user)

        if RequestFollow.objects.filter(user=user, follower=follower).exists():
            RequestFollow.objects.filter(user=user, follower=follower).delete()
            return redirect('/profile/' + user)

        if is_private:
            RequestFollow.objects.create(user=user, follower=follower)
        else:
            FollowersCount.objects.create(user=user, follower=follower)

        return redirect('/profile/' + user)

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

@login_required(login_url='signin')
def delete_post(request):
    if request.method == 'POST':
        post_id = request.POST.get('post_id')
        post = Post.objects.get(id=post_id)
        if post.user == request.user.username:
            post.delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required(login_url='signin')
def explore(request):
    user_object = User.objects.get(username=request.user.username)
    user_profile = Profile.objects.get(user=user_object)

    user_profile_post = Profile.objects.filter(private_public=False)
    posts = []

    for user in user_profile_post:
        if not user.private_public:
            posts.append(Post.objects.filter(user=user.user))


    user_following = FollowersCount.objects.filter(follower=request.user.username)
    for user in user_following:
        posts.append(Post.objects.filter(user=user.user))

    posts = list(set(chain(*posts)))

    random.shuffle(posts)
    posts = posts[:50]

    return render(request, 'explore.html', {'user_profile': user_profile,'posts': posts})

@login_required(login_url='signin')
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

@login_required(login_url='signin')
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

@login_required(login_url='signin')
def post(request,post_id):
    if not request.user.is_authenticated:
        return redirect('login')
    try:
        user_object = User.objects.get(username=request.user.username)
        user_profile = Profile.objects.get(user=user_object)
        user_follow = FollowersCount.objects.filter(user=user_object, follower=request.user.username)
        post = ''
        if user_profile.private_public or not user_follow.exists():
            post = Post.objects.filter(id=post_id).prefetch_related('comments__user__profile')



        posts = list(Post.objects.exclude(id=post_id).order_by('?')[:3])

        return render(request, 'post.html', {'user_profile': user_profile,'posts': post,'other_posts': posts})
    except Post.DoesNotExist:
        return redirect('/')

@login_required(login_url='signin')
def myFavorite(request):
    if not request.user.is_authenticated:
        return redirect('login')
    try:
        user_object = User.objects.get(username=request.user.username)
        user_profile = Profile.objects.get(user=user_object)
        posts = Post.objects.filter(myfavorite__user=request.user)
        print(posts)
        return render(request, 'my_favorite.html', {'user_profile': user_profile, 'posts': posts})
    except Post.DoesNotExist:
        return redirect('/')

@login_required(login_url='signin')
def myFavoriteAdd(request,post_id):
    if not request.user.is_authenticated:
        return redirect('login')

    post = get_object_or_404(Post, id=post_id)

    is_favorite = MyFavorite.objects.filter(user=request.user, post=post).exists()

    if is_favorite:
        MyFavorite.objects.filter(user=request.user, post=post).delete()
    else:
        MyFavorite.objects.create(user=request.user, post=post)

    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required(login_url='signin')
def comfirmEmail(request):
    verification_code = ''.join(random.choices('0123456789', k=6))

    expiry_time = (timezone.now() + timedelta(minutes=2)).isoformat()

    request.session['verification_code'] = {
        'code': verification_code,
        'expire_at': expiry_time,
    }
    subject = 'کد تایید حساب کاربری'
    message = f'کد تایید شما برای ورود به سایت: {verification_code}'
    email_from = django_settings.EMAIL_HOST_USER
    recipient_list = [request.user.email, ]

    try:
        send_mail(subject, message, email_from, recipient_list)
        messages.error(request, 'ایمیل با موفقیت ارسال شد.')
        print("ایمیل با موفقیت ارسال شد.")
        return render(request,'verify_email.html')
    except Exception as e:
        print(f"خطا در ارسال ایمیل: {e}")
        messages.error(request, 'خطا در ارسال ایمیل')
        return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required(login_url='signin')
def verifyEmail(request):
    if request.method == 'POST':
        user_code = request.POST.get('verification_code')
        stored_code_data = request.session.get('verification_code')

        if stored_code_data:
            stored_expiry_time = datetime.fromisoformat(stored_code_data['expire_at'])
            if timezone.now() > stored_expiry_time:
                del request.session['verification_code']
                messages.error(request, 'کد منقضی شده است. لطفاً دوباره درخواست دهید.')
                return redirect(request.META.get('HTTP_REFERER', '/'))

            elif user_code == stored_code_data['code']:
                try:
                    user_profile = Profile.objects.get(user=request.user)
                    user_profile.email_confirmed = True
                    user_profile.save()

                    del request.session['verification_code']
                    messages.success(request, 'ایمیل شما با موفقیت تایید شد!')
                except Profile.DoesNotExist:
                    messages.error(request, 'پروفایل کاربر یافت نشد.')

                return redirect('settings')
            else:
                messages.error(request, 'کد وارد شده صحیح نیست. لطفاً دوباره تلاش کنید.')
                return render(request, 'verify_email.html')
        else:
            messages.error(request, 'خطا: کدی برای تایید وجود ندارد.')

    return render(request,'verify_email.html')

@login_required(login_url='signin')
def verifyPhone(request):
    if request.method == 'POST':
        user_phone = request.POST.get('verification_phone')

        if len(user_phone) < 10:
            messages.error(request, 'شماره تلفن نامعتبر است.')
            return redirect(request.META.get('HTTP_REFERER', '/'))

        verification_code = ''.join(random.choices('0123456789', k=6))

        expiry_time = (timezone.now() + timedelta(minutes=2)).isoformat()

        request.session['verification_code'] = {
                'code': verification_code,
                'expire_at': expiry_time,
                'phone': user_phone,
        }
        message = f'کد تایید شما برای ورود به سایت: {verification_code}'
        encoded_message = quote(message)
        conn = http.client.HTTPSConnection("api.sms.ir")
        payload = ''
        headers = {
            'Accept': 'text/plain'
        }
        conn.request(
            "GET",
            f"/v1/send?username=9039078303&password=NKHkqSgfOEKZ2QdA7ecPoDdUBeZRny2nVl5ASphMpNxI18YR&mobile={user_phone}&line=30002108002701&text={encoded_message}",
            payload,
            headers
        )
        res = conn.getresponse()
        data = res.read()
        print(data.decode("utf-8"))
        return render(request,'confirm_phone.html')
    else:
        return render(request,'verify_phone.html')

@login_required(login_url='signin')
def confirmPhone(request):
    try:
        user_code = request.POST.get('verification_code')
        user_phone = request.session.get('verification_code')
        phone_number = user_phone['phone']
        stored_code_data = request.session.get('verification_code')
        if stored_code_data:
            stored_expiry_time = datetime.fromisoformat(stored_code_data['expire_at'])
            if timezone.now() > stored_expiry_time:
                del request.session['verification_code']
                messages.error(request, 'کد منقضی شده است. لطفاً دوباره درخواست دهید.')
                return redirect(request.META.get('HTTP_REFERER', '/'))

            elif user_code == stored_code_data['code']:
                user_profile = Profile.objects.get(user=request.user)
                user_profile.phone_confirmed = True
                user_profile.phone_number = phone_number
                user_profile.save()

                del request.session['verification_code']
                messages.success(request, 'شماره شما با موفقیت تایید شد!')

                return redirect('settings')
            else:
                messages.error(request, 'کد وارد شده صحیح نیست. لطفاً دوباره تلاش کنید.')
                return render(request, 'verify_email.html')
        else:
            messages.error(request, 'خطا: کدی برای تایید وجود ندارد.')
    except Profile.DoesNotExist:
        messages.error(request, 'پروفایل کاربر یافت نشد.')

@login_required(login_url='signin')
def changePassword(request):
    if request.method == 'POST':
        try:
            old_password = request.POST.get('old_password')
            old_password_1 = request.POST.get('old_password_1')
            new_password = request.POST.get('new_password')
            new_password_1 = request.POST.get('new_password_1')

            user = User.objects.get(username=request.user.username)

            if old_password != old_password_1 or new_password != new_password_1:
                messages.error(request, 'passwords not match')
                return render(request, 'change_password.html')
            elif not check_password(old_password, user.password):
                messages.error(request, 'old passwords not match')
                return render(request, 'change_password.html')
            elif len(new_password) < 8:
                messages.error(request, 'new password is too short')
                return render(request, 'change_password.html')
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, 'changed password')
                return redirect(request.META.get('HTTP_REFERER', '/'))
        except User.DoesNotExist:
            messages.error(request, 'ERROR')
            return redirect(request.META.get('HTTP_REFERER', '/'))
    return render(request, 'change_password.html')

@login_required(login_url='signin')
def end_session(request, session_key):
    if request.method == 'POST':
        session = get_object_or_404(Session, session_key=session_key)

        if session.get_decoded().get('_auth_user_id') == str(request.user.id):
            session.delete()

    return redirect('/')

@login_required(login_url='signin')
def forgotPassword(request):
    if request.method == 'POST':
        user_code = request.POST.get('code')
        stored_code_data = request.session.get('verification_password_code')
        new_password = request.POST.get('new_password')
        new_password_1 = request.POST.get('new_password_1')

        if stored_code_data:
            stored_expiry_time = datetime.fromisoformat(stored_code_data['expire_at'])
            if timezone.now() > stored_expiry_time:
                del request.session['verification_password_code']
                messages.error(request, 'کد منقضی شده است. لطفاً دوباره درخواست دهید.')
                return redirect(request.META.get('HTTP_REFERER', '/'))

            elif user_code != stored_code_data['code']:
                messages.error(request, 'code is not valid')
                return render(request, 'forgot_password.html')
            elif new_password != new_password_1:
                messages.error(request, 'passwords not match')
                return render(request, 'forgot_password.html')
            elif len(new_password) < 8:
                messages.error(request, 'new password is too short')
                return render(request, 'forgot_password.html')
            else:
                try:
                    user = User.objects.get(username=request.user.username)
                    user.set_password(new_password)
                    user.save()
                    del request.session['verification_password_code']
                    messages.success(request, 'changed password')
                except Profile.DoesNotExist:
                    messages.error(request, 'پروفایل کاربر یافت نشد.')

                return redirect('settings')
        else:
            messages.error(request, 'کد وارد شده صحیح نیست. لطفاً دوباره تلاش کنید.')
            return render(request, 'verify_email.html')

    else:
        verification_code = ''.join(random.choices('0123456789', k=6))

        expiry_time = (timezone.now() + timedelta(minutes=2)).isoformat()

        request.session['verification_password_code'] = {
            'code': verification_code,
            'expire_at': expiry_time,
        }
        subject = 'کد تایید تغییر رمز'
        message = f'کد تایید شما : {verification_code}'
        email_from = django_settings.EMAIL_HOST_USER
        recipient_list = [request.user.email, ]

        try:
            send_mail(subject, message, email_from, recipient_list)
            messages.error(request, 'ایمیل با موفقیت ارسال شد.')
            print("ایمیل با موفقیت ارسال شد.")
            return render(request, 'forgot_password.html')
        except Exception as e:
            print(f"خطا در ارسال ایمیل: {e}")
            messages.error(request, 'خطا در ارسال ایمیل')
            return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required(login_url='signin')
def privatePublic(request):
    user_profile = Profile.objects.get(user=request.user)
    if user_profile.private_public:
        user_profile.private_public = False
        user_profile.save()
    else:
        user_profile.private_public = True
        user_profile.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required(login_url='signin')
@require_POST
def acceptRequest(request,pk):
    if request.method == 'POST':
        user_follower = User.objects.get(username=pk)
        user_request = RequestFollow.objects.get(user=request.user,follower=user_follower)
        user_follower = FollowersCount.objects.create(user=request.user.username, follower=user_request.follower)
        user_follower.save()
        user_request.delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required(login_url='signin')
def following(request, pk):
    user_object = User.objects.get(username=request.user.username)
    user_profile = Profile.objects.get(user=user_object)

    followed_usernames = FollowersCount.objects.filter(
        follower=pk
    ).values_list('user', flat=True)

    profiles = Profile.objects.filter(user__username__in=followed_usernames)

    return render(request, 'following.html', {
        'profiles': profiles,
        'user_profile': user_profile
    })

@login_required(login_url='signin')
def followers(request,pk):
    user_object = User.objects.get(username=request.user.username)
    user_profile = Profile.objects.get(user=user_object)

    followed_usernames = FollowersCount.objects.filter(
        user=pk
    ).values_list('follower', flat=True)

    profiles = Profile.objects.filter(user__username__in=followed_usernames)

    return render(request, 'following.html', {
        'profiles': profiles,
        'user_profile': user_profile
    })

@login_required(login_url='signin')
def messageRoom(request, room_name):
    user_object = User.objects.get(username=request.user.username)
    user_profile = Profile.objects.get(user=user_object)
    other_user = User.objects.get(username=room_name)
    other_user_profile = Profile.objects.get(user=other_user)

    conversation_qs = Conversation.objects.filter(participants=request.user).filter(participants=other_user)
    if conversation_qs.exists():
        conversation = conversation_qs.first()
    else:
        conversation = Conversation.objects.create()
        conversation.participants.set([request.user, other_user])
        conversation.save()

    messages = conversation.messages.all().order_by('timestamp')

    return render(request, "messages.html", {
        "room_name": room_name,
        "user_profile": user_profile,
        "other_user_profile": other_user_profile,
        "messages": messages
    })

@login_required(login_url='signin')
def messagesChat(request):
    user_object = User.objects.get(username=request.user.username)
    user_profile = Profile.objects.get(user=user_object),

    user = request.user
    conversations = Conversation.objects.filter(participants=user)

    chat_list = []
    for conv in conversations:
        other_users = conv.participants.exclude(id=user.id)
        for other_user in other_users:
            profile = Profile.objects.get(user=other_user)
            last_msg = conv.messages.last()
            chat_list.append({
                'profile': profile,
                'last_message': last_msg,
                'user_profile':user_profile,
            })

    return render(request, 'chats.html', {
        'user_profile': user_profile,
        'chat_list': chat_list,
    })


@login_required(login_url='signin')
@require_POST
def messageSend(request, room_name):
    try:
        other_user = User.objects.get(username=room_name)

        MAX_FILE_SIZE = 100 * 1024 * 1024  # 5MB
        file = request.FILES.get('file', None)

        if file and file.size > MAX_FILE_SIZE:
            messages.error(request, 'حجم فایل باید کمتر از 100 مگابایت باشد')
            return redirect('message_room', room_name=room_name)

        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        ).distinct().first()

        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, other_user)

        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            text=request.POST.get('text', ''),
            file=file
        )

        return redirect('message_room', room_name=room_name)

    except User.DoesNotExist:
        messages.error(request, 'کاربر مورد نظر یافت نشد')
        return redirect('message_room', room_name=room_name)

@login_required(login_url='signin')
@require_POST
def messagesDelete(request, message_id):
    message = Message.objects.get(id=message_id,sender=request.user)
    if message is None:
        messages.error(request, 'sometimes wet wrong')
    message.delete()
    return redirect(request.META.get('HTTP_REFERER', '/'))
