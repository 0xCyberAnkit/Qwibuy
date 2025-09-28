from . import views
from django.urls import path

urlpatterns = [
    path('',views.index,name='webcode'),
    path('shop/',views.shop,name='webcode'),
    path('profile/',views.profile,name='webcode'),
    path('portal/',views.portal,name='webcode'),
    path('auth/',views.auth,name='webcode'),
    path("get_recommendations/", views.get_recommendations, name="get_recommendations"),
    path("simulate_purchase/", views.get_recommendations, name="get_recommendations"),
]
