from django import forms
from .models import Article, Collection

class ArticleSearchForm(forms.Form):
    query = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Поиск по заголовкам и тексту...',
        'class': 'search-input'
    }))
    category = forms.ChoiceField(required=False, choices=[])
    source = forms.ChoiceField(required=False, choices=[])
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Category, Source
        self.fields['category'].choices = [('', 'Все категории')] + [
            (c.id, c.name) for c in Category.objects.all()
        ]
        self.fields['source'].choices = [('', 'Все источники')] + [
            (s.id, s.name) for s in Source.objects.filter(is_active=True)
        ]

class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['name', 'description', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название подборки'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание (необязательно)'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }