from django import forms
from .models import Makale
from .models import Degerlendirme
from django import forms
from .models import Mesaj

class MakaleForm(forms.ModelForm):
    class Meta:
        model = Makale
        fields = ['eposta', 'dosya']


class DegerlendirmeForm(forms.ModelForm):
    class Meta:
        model = Degerlendirme
        fields = [ 'yorum']
        
class TakipForm(forms.Form):
    eposta = forms.EmailField(label='E-posta')
    takip_numarasi = forms.UUIDField(label='Takip Numarası')  
    
    
class RevizeForm(forms.ModelForm):
    class Meta:
        model = Makale
        fields = ['revize_dosya']



class MesajForm(forms.ModelForm):
    class Meta:
        model = Mesaj
        fields = ['icerik']

