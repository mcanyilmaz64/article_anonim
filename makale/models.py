from django.db import models
import uuid

HAKEMLER = [
        ('hakem1', 'Hakem 1'),
        ('hakem2', 'Hakem 2'),
        ('hakem3', 'Hakem 3'),
    ]

class Makale(models.Model):
    takip_numarasi = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    eposta = models.EmailField()
    dosya = models.FileField(upload_to='makaleler/')
    yuklenme_tarihi = models.DateTimeField(auto_now_add=True)
    revize_dosya = models.FileField(upload_to='revizeler/', null=True, blank=True)
    durum = models.CharField(max_length=50, default="Yüklendi")  # Örn: Yüklendi, İnceleniyor, Kabul, Reddedildi
    anonim_dosya = models.FileField(upload_to='anonim/', null=True, blank=True)
    mesaj = models.TextField(null=True, blank=True)
    keywords = models.CharField(max_length=500, blank=True, null=True)
    yorumlu_pdf = models.FileField(upload_to='yorumlu/', blank=True, null=True)
    final_pdf = models.FileField(upload_to='final/', blank=True, null=True)
    atandigi_hakem = models.CharField(max_length=10, choices=HAKEMLER, null=True, blank=True)

    




    def __str__(self):
        return f"{self.eposta} - {self.takip_numarasi}"

class Degerlendirme(models.Model):
    makale = models.ForeignKey(Makale, on_delete=models.CASCADE)
    hakem_adi = models.CharField(max_length=100)
    yorum = models.TextField()
    tarih = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.hakem_adi} → {self.makale.takip_numarasi}"
