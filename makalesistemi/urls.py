"""
URL configuration for makalesistemi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from makale import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.makale_yukle, name='makale_yukle'),
    path('editor/', views.editor_paneli, name='editor_paneli'),
    path('anonimlestir/<int:makale_id>/', views.anonimlestir_custom, name='anonimlestir_custom'),
    path('anonim-sec/<int:makale_id>/', views.anonimlestirme_ayar, name='anonimlestirme_secim'),
    path('makale/sil/<int:makale_id>/', views.makale_sil, name='makale_sil'),
    path('hakem/', views.hakem_paneli, name='hakem_paneli'),
    path('hakem/degerlendir/<int:makale_id>/', views.makale_degerlendir, name='makale_degerlendir'),
    path('sorgula/', views.makale_sorgula, name='makale_sorgula'),
    path('revize_yukle/<int:makale_id>/', views.revize_yukle, name='revize_yukle'),
    path('final_olustur/<int:makale_id>/', views.final_pdf_olustur_view, name='final_olustur'),
    path('hakem_ata/<int:makale_id>/', views.hakem_ata, name='hakem_ata'),
    path('log-kayitlari/', views.log_kayitlari, name='log_kayitlari'),
    path('mesajlar/<int:makale_id>/', views.mesajlar, name='mesajlar'),
    path('revizeyi_hakeme_gonder/<int:makale_id>/', views.revizeyi_hakeme_gonder, name='revizeyi_hakeme_gonder'),
    path("mesaj-cevapla/<int:makale_id>/", views.mesaj_cevapla, name="mesaj_cevapla"),
    path('editor/alan/<int:makale_id>/', views.alan_ata, name='alan_ata'),



    
    


]

# Dosya yüklemeleri için:
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

