from django.shortcuts import render, redirect
from .forms import MakaleForm, DegerlendirmeForm, TakipForm, RevizeForm
from .models import Makale, Degerlendirme
import fitz  # PyMuPDF
import spacy
import re
import os
from django.conf import settings
from django.http import FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.http import HttpRequest, FileResponse




# 🔹 spaCy modelini yükle (Transformer tabanlı, yüksek doğruluklu)
nlp = spacy.load("en_core_web_trf")

def makale_yukle(request):
    if request.method == 'POST':
        form = MakaleForm(request.POST, request.FILES)
        if form.is_valid():
            makale = form.save()

            # Anahtar kelimeleri PDF'ten çek
            pdf_path = os.path.join(settings.MEDIA_ROOT, makale.dosya.name)
            keywords = extract_keywords_from_pdf(pdf_path)

            if keywords:
                makale.keywords = keywords
                makale.save()

            return render(request, 'makale/yukleme_basarili.html', {'takip': makale.takip_numarasi})
    else:
        form = MakaleForm()
    return render(request, 'makale/makale_yukle.html', {'form': form})

# 🔹 Editör paneli
def editor_paneli(request):
    makaleler = Makale.objects.all().order_by('-yuklenme_tarihi')
    return render(request, 'makale/editor_paneli.html', {'makaleler': makaleler})

# 🔹 Hakem paneli
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


# 🔹 Hakem değerlendirme sayfası
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
            makale.save()

            return render(request, 'makale/degerlendirme_basarili.html')
    else:
        form = DegerlendirmeForm()
    return render(request, 'makale/makale_degerlendir.html', {'form': form, 'makale': makale})

# 🔹 Yazar makale durum sorgulama
def makale_sorgula(request):
    sonuc = None
    yorum = None

    if request.method == 'POST':
        form = TakipForm(request.POST)
        if form.is_valid():
            eposta = form.cleaned_data['eposta']
            takip = form.cleaned_data['takip_numarasi']
            try:
                makale = Makale.objects.get(eposta=eposta, takip_numarasi=takip)
                sonuc = makale
                degerlendirmeler = Degerlendirme.objects.filter(makale=makale).order_by('id')  # veya -id, son yorum üstte olsun diye

            except Makale.DoesNotExist:
                sonuc = "bulunamadi"
    else:
        form = TakipForm()

    return render(request, 'makale/sorgula.html', {
        'form': form,
        'sonuc': sonuc,
        'yorum': yorum
    })

def revize_yukle(request, makale_id):
    makale = Makale.objects.get(id=makale_id)
    if request.method == 'POST':
        form = RevizeForm(request.POST, request.FILES, instance=makale)
        if form.is_valid():
            form.save()
            makale.durum = "Revize Yüklendi"
            makale.save()
            return redirect('makale_sorgula')  # tekrar sorguya yönlendir
    else:
        form = RevizeForm()
    return render(request, 'makale/revize_yukle.html', {'form': form, 'makale': makale})

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
            for kelime in secilenler:
                rects = page.search_for(kelime)
                for rect in rects:
                    yildizli = '*' * len(kelime)
                    page.add_redact_annot(rect, fill=(1, 1, 1))  # Beyaz arka plan
                    page.apply_redactions()
                    page.insert_textbox(rect, yildizli, fontsize=11, color=(0, 0, 0))

        doc.save(yeni_pdf_yolu)
        doc.close()

        # 🔹 Veritabanına kaydet!
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

    patterns = [
        r"(?i)(keywords[\s\-_:]*)\s*(.*)",
        r"(?i)(keywords-component[\s\-_:]*)\s*(.*)",
        r"(?i)(index terms[\s\-_:]*)\s*(.*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            # Satırın tamamı eşleşmiş olabilir, yalnızca son kısmı al
            full = match.group(0)
            parts = re.split(r"[:-]", full, 1)
            if len(parts) > 1:
                return parts[1].strip()

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
        makale.save()
    return redirect('editor_paneli')