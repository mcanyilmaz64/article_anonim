from django import forms
from .models import Makale
from .models import Degerlendirme

class MakaleForm(forms.ModelForm):
    class Meta:
        model = Makale
        fields = ['eposta', 'dosya', 'mesaj']


class DegerlendirmeForm(forms.ModelForm):
    class Meta:
        model = Degerlendirme
        fields = ['hakem_adi', 'yorum']
        
class TakipForm(forms.Form):
    eposta = forms.EmailField(label="E-posta")
    takip_numarasi = forms.UUIDField(label="Takip Numarası")
    
class RevizeForm(forms.ModelForm):
    class Meta:
        model = Makale
        fields = ['revize_dosya']
