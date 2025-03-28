from django.shortcuts import render, redirect
from .forms import MakaleForm, DegerlendirmeForm, TakipForm, RevizeForm
from .models import Makale, Degerlendirme
import fitz  
import spacy
import re
import os
from django.conf import settings
from django.http import FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.http import HttpRequest, FileResponse
from django.utils import timezone 
from .models import Mesaj
from .forms import MesajForm
import hashlib
from django.views.decorators.http import require_POST
import uuid





nlp = spacy.load("en_core_web_trf")

def makale_yukle(request):
    if request.method == 'POST':
        form = MakaleForm(request.POST, request.FILES)
        if form.is_valid():
            makale = form.save(commit=False)
            makale.log_editore_gelis = timezone.now()

            makale.takip_numarasi = uuid.uuid4()
            makale.sha256_hash = makale.takip_numarasi  # 3. aynı hash'i eşleşme için kullan


            # ✉️ E-posta'yı hashle
            makale.eposta = hash_email(makale.eposta)

            # Dosya hash işlemleri
            makale.save()  # Dosya yolu oluşması için önce kaydet
            pdf_path = os.path.join(settings.MEDIA_ROOT, makale.dosya.name)
            makale.pdf_hash = hesapla_dosya_sha256(pdf_path)

            # Anahtar kelime çıkar
            keywords = extract_keywords_from_pdf(pdf_path)
            if keywords:
                makale.keywords = keywords

            makale.save()  # Tüm alanlar güncellendiğinde tekrar kaydet

            return render(request, 'makale/yukleme_basarili.html', {'takip': makale.takip_numarasi})
    else:
        form = MakaleForm()
        
    return render(request, 'makale/makale_yukle.html', {'form': form})

def editor_paneli(request):
    makaleler = Makale.objects.all().order_by('-yuklenme_tarihi')
    return render(request, 'makale/editor_paneli.html', {'makaleler': makaleler})

def hakem_paneli(request):
    hakem_adi = request.GET.get("hakem")  # ?hakem=hakem1 gibi URL parametresi

    if hakem_adi:
        makaleler = Makale.objects.filter(atandigi_hakem=hakem_adi)
    else:
        makaleler = []

    return render(request, 'makale/hakem_paneli.html', {
        'makaleler': makaleler,
        'hakem': hakem_adi
    })

def makale_degerlendir(request, makale_id):
    makale = Makale.objects.get(id=makale_id)
    if request.method == 'POST':
        form = DegerlendirmeForm(request.POST)
        if form.is_valid():
            deger = form.save(commit=False)
            deger.makale = makale
            deger.save()
            
            hakem_yorumu_ekle_pdf(makale, deger.yorum)

            makale.durum = "Değerlendirildi"
            makale.log_hakem_cevap = timezone.now()
            makale.save()

            return render(request, 'makale/degerlendirme_basarili.html')
    else:
        form = DegerlendirmeForm()
    return render(request, 'makale/makale_degerlendir.html', {'form': form, 'makale': makale})

@csrf_exempt
def makale_sorgula(request):
    sonuc = None
    yorumlar = None

    if request.method == 'POST':
        form = TakipForm(request.POST)
        if form.is_valid():
            eposta = hash_email(form.cleaned_data['eposta'])
            takip = form.cleaned_data['takip_numarasi']

            try:
                makale = Makale.objects.get(eposta=eposta, takip_numarasi=takip)
                sonuc = makale
                yorumlar = Degerlendirme.objects.filter(makale=makale)

                # Eğer kullanıcı mesaj yazdıysa
                if 'icerik' in request.POST:
                    icerik = request.POST.get('icerik', '').strip()
                    if icerik:
                        makale.mesaj = icerik
                        makale.mesaj_gonderen = 'yazar'
                        makale.save()
                        return redirect('makale_sorgula')  # Sayfayı yenile

            except Makale.DoesNotExist:
                sonuc = "bulunamadi"
    else:
        form = TakipForm()

    return render(request, 'makale/sorgula.html', {
        'form': form,
        'sonuc': sonuc,
        'yorum': yorumlar,
    })


def revize_yukle(request, makale_id):
    makale = Makale.objects.get(id=makale_id)
    if request.method == 'POST':
        form = RevizeForm(request.POST, request.FILES, instance=makale)
        if form.is_valid():
            form.save()
            makale.durum = "Revize Yüklendi"
            makale.dosya = makale.revize_dosya
            makale.save()
            return redirect('makale_sorgula')  # tekrar sorguya yönlendir
    else:
        form = RevizeForm(instance=makale)
    return render(request, 'makale/revize_yukle.html', {'form': form, 'makale': makale})

@require_POST
def revizeyi_hakeme_gonder(request, makale_id):
    makale = get_object_or_404(Makale, id=makale_id)
    makale.revize_hakeme_atildi = True
    makale.log_hakeme_atis = timezone.now()
    makale.save()
    return redirect('editor_paneli')  # Editör paneli URL ismi neyse onu kullan

def anonimlestirme_ayar(request, makale_id):
    makale = Makale.objects.get(id=makale_id)
    doc = fitz.open(makale.dosya.path)

    full_text = ""
    for page in doc:
        full_text += page.get_text("text")
    doc.close()

    nlp_doc = nlp(full_text)

    persons = list(set([ent.text for ent in nlp_doc.ents if ent.label_ == "PERSON"]))
    orgs = list(set([ent.text for ent in nlp_doc.ents if ent.label_ == "ORG"]))
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", full_text)
    keywords = extract_keywords_from_pdf(makale.dosya.path)

    return render(request, 'makale/anonimlestirme_secim.html', {
        'makale': makale,
        'persons': persons,
        'orgs': orgs,
        'emails': emails,
        'keywords': keywords 
    })

@csrf_exempt
def anonimlestir_custom(request, makale_id):
    if request.method == 'POST':
        makale = Makale.objects.get(id=makale_id)
        secilenler = request.POST.getlist('secilenler')

        dosya_yolu = makale.dosya.path
        anonim_klasor = os.path.join(settings.MEDIA_ROOT, 'anonim')
        os.makedirs(anonim_klasor, exist_ok=True)
        yeni_pdf_yolu = os.path.join(anonim_klasor, f"anonim_{makale.id}.pdf")

        doc = fitz.open(dosya_yolu)

        for page in doc:
            rect_yildiz_listesi = []  # ⭐️ Koordinatları ve yıldızlı halleri saklayacağız

            # 1. Rect'leri topla ve redact annotasyon ekle
            for kelime in secilenler:
                rects = page.search_for(kelime)
                for rect in rects:
                    page.add_redact_annot(rect, fill=(1, 1, 1))  # beyaz arka plan
                    rect_yildiz_listesi.append((rect, '*' * len(kelime)))

            page.apply_redactions()  # ❗ Arka planı beyazla, metni sil

            # 2. Şimdi saklanan rect'lere yıldızlı metin ekle
            for rect, yildiz in rect_yildiz_listesi:
                page.insert_textbox(rect, yildiz, fontsize=11, color=(0, 0, 0), fontname="helv", align=0)

        doc.save(yeni_pdf_yolu)
        doc.close()

        # 🔹 Veritabanına kaydet
        makale.anonim_dosya.name = f"anonim/anonim_{makale.id}.pdf"
        makale.durum = "Değerlendirme Bekleniyor"
        makale.save()

        return FileResponse(open(yeni_pdf_yolu, 'rb'), content_type='application/pdf')

def makale_sil(request, makale_id):
    makale = get_object_or_404(Makale, id=makale_id)
    makale.delete()
    messages.success(request, "Makale başarıyla silindi.")
    return redirect('editor_paneli')

def extract_keywords_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""

    for page in doc:
        text += page.get_text("text")

    doc.close()

    text = text.replace("\n", " ")  # çok satırlı yazımı önler

    # Olası başlık varyasyonları
    patterns = [
        r"(?:Keywords|Key words|Index Terms)[\s\-–—_:]*([\w\s,;]+)",  # genel eşleşme
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # İlk anlamlı eşleşmeyi döndür
            for match in matches:
                cleaned = match.strip()
                if len(cleaned) > 3:
                    return cleaned

    return None


def hakem_yorumu_ekle_pdf(makale, yorum):
  

    anonim_pdf_yolu = os.path.join(settings.MEDIA_ROOT, makale.anonim_dosya.name)
    yorumlu_pdf_yolu = os.path.join(settings.MEDIA_ROOT, f"yorumlu_anonim_{makale.id}.pdf")

    doc = fitz.open(anonim_pdf_yolu)

    # Yeni bir sayfa oluştur ve yorum ekle
    yorum_sayfa = doc.new_page()

    # Dikdörtgen alan (sol, üst, sağ, alt) – sayfa içinde yorumun yazılacağı alan
    textbox_rect = fitz.Rect(72, 72, 500, 800)

    yorum_sayfa.insert_textbox(
        textbox_rect,
        f"Hakem Yorumu:\n\n{yorum}",
        fontsize=12,
        fontname="helv",  # Helvetica
        color=(0, 0, 0),
        align=0  # sola yaslı
    )

    doc.save(yorumlu_pdf_yolu)
    doc.close()

    # Makaleye kaydet
    makale.yorumlu_pdf.name = f"yorumlu_anonim_{makale.id}.pdf"
    makale.yorumlu_pdf_hash = hesapla_dosya_sha256(yorumlu_pdf_yolu)
    makale.save()

def final_pdf_olustur(makale):
    orijinal_yol = os.path.join(settings.MEDIA_ROOT, makale.dosya.name)
    yorumlu_yol = os.path.join(settings.MEDIA_ROOT, makale.yorumlu_pdf.name)
    final_yol = os.path.join(settings.MEDIA_ROOT, f"final/final_{makale.id}.pdf")

    # Final klasörünü oluştur
    os.makedirs(os.path.dirname(final_yol), exist_ok=True)

    orijinal = fitz.open(orijinal_yol)
    yorumlu = fitz.open(yorumlu_yol)

    # Sadece yorumlu PDF’in son sayfasını al
    son_sayfa = yorumlu[-1]
    orijinal.insert_pdf(yorumlu, from_page=len(yorumlu) - 1, to_page=len(yorumlu) - 1)

    orijinal.save(final_yol)
    orijinal.close()
    yorumlu.close()

    # Veritabanına kaydet
    makale.final_pdf.name = f"final/final_{makale.id}.pdf"
    makale.final_pdf_hash = hesapla_dosya_sha256(final_yol)
    makale.log_yayim = timezone.now()

    makale.save()

def final_pdf_olustur_view(request, makale_id):
    makale = Makale.objects.get(id=makale_id)
    final_pdf_olustur(makale)
    return FileResponse(open(os.path.join(settings.MEDIA_ROOT, makale.final_pdf.name), 'rb'), content_type='application/pdf')

def hakem_ata(request, makale_id):
    makale = Makale.objects.get(id=makale_id)
    if request.method == 'POST':
        secilen_hakem = request.POST.get('hakem')
        makale.atandigi_hakem = secilen_hakem
        makale.log_hakeme_atis = timezone.now()

         
        if makale.revize_dosya and not makale.revize_hakeme_atildi:
            makale.revize_hakeme_atildi = True
        makale.save()
        
    return redirect('editor_paneli')

def log_kayitlari(request):
    
    makaleler = Makale.objects.all().order_by('-yuklenme_tarihi')
    return render(request, 'makale/log_kayitlari.html', {'makaleler': makaleler})
def mesajlar(request, makale_id):
    makale = get_object_or_404(Makale, id=makale_id)
    mesajlar = makale.mesajlar.order_by('tarih')  # related_name='mesajlar' sayesinde

    if request.method == 'POST':
        form = MesajForm(request.POST)
        if form.is_valid():
            mesaj = form.save(commit=False)
            mesaj.makale = makale
            mesaj.save()
            return redirect('mesajlar', makale_id=makale.id)
    else:
        form = MesajForm()

    return render(request, 'makale/mesajlar.html', {
        'makale': makale,
        'mesajlar': mesajlar,
        'form': form
    })

@csrf_exempt
def mesaj_cevapla(request, makale_id):
    makale = get_object_or_404(Makale, id=makale_id)
    if request.method == "POST":
        icerik = request.POST.get("icerik", "")
        if icerik:
            makale.mesaj = icerik
            makale.mesaj_gonderen = "editor"
            makale.save()
    return redirect("editor_paneli")

def alan_ata(request, makale_id):
    makale = get_object_or_404(Makale, id=makale_id)

    if request.method == 'POST':
        makale.alan = request.POST.get('alan')
        makale.save()
    
    return redirect('editor_paneli')

# yardımcı fonksiyonlar
#/////////////////////////////////////////////////////////////
def hesapla_sha256(veri: str) -> str:
   return hashlib.sha256(str(veri).encode('utf-8')).hexdigest() 
def hesapla_dosya_sha256(dosya_yolu: str) -> str:
    sha256 = hashlib.sha256()
    with open(dosya_yolu, 'rb') as f:
        for blok in iter(lambda: f.read(4096), b""):
            sha256.update(blok)
    return sha256.hexdigest()
def hash_email(email):
    return hashlib.sha256(email.encode('utf-8')).hexdigest()
def generate_hashed_uuid():
    random_uuid = str(uuid.uuid4())
    return hashlib.sha256(random_uuid.encode('utf-8')).hexdigest()
