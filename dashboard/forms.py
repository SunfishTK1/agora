"""
Django forms for the dashboard interface.
Professional forms with validation and user-friendly widgets.
"""

from django import forms
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from urllib.parse import urlparse
import json

from scraper.models import Domain, ScrapingTemplate


class DomainForm(forms.ModelForm):
    """Form for creating and editing domain configurations."""
    
    class Meta:
        model = Domain
        fields = [
            'name', 'base_url', 'protocol', 'max_depth', 'max_pages',
            'scrape_frequency_hours', 'status', 'advanced_config'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Company Blog, API Documentation'
            }),
            'base_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/blog/'
            }),
            'protocol': forms.Select(attrs={'class': 'form-select'}),
            'max_depth': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 20
            }),
            'max_pages': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10000
            }),
            'scrape_frequency_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 8760
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'advanced_config': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': '{\n  "user_agent": "Custom Bot",\n  "delay": 1,\n  "headers": {}\n}'
            })
        }
        
        help_texts = {
            'name': 'Descriptive name for this domain configuration',
            'base_url': 'Starting URL for scraping (must be a valid URL)',
            'max_depth': 'Maximum number of subpath levels to follow',
            'max_pages': 'Maximum number of pages to scrape per session',
            'scrape_frequency_hours': 'How often to scrape (in hours)',
            'advanced_config': 'Advanced configuration in JSON format (optional)'
        }
    
    def clean_base_url(self):
        """Validate and normalize the base URL."""
        url = self.cleaned_data['base_url']
        
        try:
            # Basic URL validation
            validator = URLValidator()
            validator(url)
            
            # Parse URL to check components
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValidationError('URL must include protocol and domain')
                
            # Ensure HTTPS for security (unless specifically HTTP)
            if parsed.scheme not in ['http', 'https']:
                raise ValidationError('Only HTTP and HTTPS protocols are supported')
                
            return url
            
        except Exception as e:
            raise ValidationError(f'Invalid URL: {str(e)}')
    
    def clean_advanced_config(self):
        """Validate advanced configuration JSON."""
        config = self.cleaned_data['advanced_config']
        
        if not config:
            return {}
            
        try:
            if isinstance(config, str):
                config = json.loads(config)
            
            # Validate config structure
            if not isinstance(config, dict):
                raise ValidationError('Advanced configuration must be a JSON object')
                
            # Check for dangerous configurations
            dangerous_keys = ['password', 'secret', 'token']
            for key in config.keys():
                if any(dangerous in key.lower() for dangerous in dangerous_keys):
                    raise ValidationError(f'Potentially sensitive key "{key}" found in configuration')
            
            return config
            
        except json.JSONDecodeError as e:
            raise ValidationError(f'Invalid JSON format: {str(e)}')
        except Exception as e:
            raise ValidationError(f'Configuration error: {str(e)}')
    
    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        
        max_depth = cleaned_data.get('max_depth')
        max_pages = cleaned_data.get('max_pages')
        frequency = cleaned_data.get('scrape_frequency_hours')
        
        # Warn about potentially intensive configurations
        if max_depth and max_pages and frequency:
            if max_depth > 5 and max_pages > 1000:
                self.add_error('max_depth', 
                    'High depth and page count may result in very long scraping sessions')
            
            if frequency < 6 and max_pages > 500:
                self.add_error('scrape_frequency_hours',
                    'Frequent scraping of many pages may overload the target server')
        
        return cleaned_data


class DomainConfigForm(forms.Form):
    """Quick configuration form for domain settings."""
    
    FREQUENCY_CHOICES = [
        (1, 'Every hour'),
        (6, 'Every 6 hours'),
        (12, 'Every 12 hours'),
        (24, 'Daily'),
        (168, 'Weekly'),
        (720, 'Monthly'),
    ]
    
    DEPTH_CHOICES = [
        (1, 'Shallow (1 level)'),
        (3, 'Medium (3 levels)'),
        (5, 'Deep (5 levels)'),
        (10, 'Very deep (10 levels)'),
    ]
    
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Domain name'
        })
    )
    
    base_url = forms.URLField(
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://example.com/path/'
        })
    )
    
    scrape_frequency_hours = forms.ChoiceField(
        choices=FREQUENCY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    max_depth = forms.ChoiceField(
        choices=DEPTH_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    max_pages = forms.IntegerField(
        initial=100,
        min_value=1,
        max_value=10000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': 50
        })
    )


class ScrapingTemplateForm(forms.ModelForm):
    """Form for creating reusable scraping templates."""
    
    class Meta:
        model = ScrapingTemplate
        fields = ['name', 'description', 'selectors', 'rules', 'is_public']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Template name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe what this template is for...'
            }),
            'selectors': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 10,
                'placeholder': '{\n  "title": "h1",\n  "content": ".article-content",\n  "author": ".author-name"\n}'
            }),
            'rules': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 8,
                'placeholder': '{\n  "follow_pagination": true,\n  "exclude_patterns": ["#comments"]\n}'
            }),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def clean_selectors(self):
        """Validate selectors JSON."""
        selectors = self.cleaned_data['selectors']
        
        try:
            if isinstance(selectors, str):
                selectors = json.loads(selectors)
            
            if not isinstance(selectors, dict):
                raise ValidationError('Selectors must be a JSON object')
                
            return selectors
            
        except json.JSONDecodeError as e:
            raise ValidationError(f'Invalid JSON format: {str(e)}')
    
    def clean_rules(self):
        """Validate rules JSON."""
        rules = self.cleaned_data['rules']
        
        if not rules:
            return {}
            
        try:
            if isinstance(rules, str):
                rules = json.loads(rules)
            
            if not isinstance(rules, dict):
                raise ValidationError('Rules must be a JSON object')
                
            return rules
            
        except json.JSONDecodeError as e:
            raise ValidationError(f'Invalid JSON format: {str(e)}')


class BulkDomainForm(forms.Form):
    """Form for bulk domain import."""
    
    urls = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'https://example1.com/blog/\nhttps://example2.com/docs/\nhttps://example3.com/api/'
        }),
        help_text='Enter one URL per line'
    )
    
    default_frequency = forms.ChoiceField(
        choices=DomainConfigForm.FREQUENCY_CHOICES,
        initial=24,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    default_depth = forms.ChoiceField(
        choices=DomainConfigForm.DEPTH_CHOICES,
        initial=3,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    default_pages = forms.IntegerField(
        initial=100,
        min_value=1,
        max_value=10000,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    auto_activate = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Automatically activate domains for scraping'
    )
    
    def clean_urls(self):
        """Validate and parse URLs."""
        urls_text = self.cleaned_data['urls']
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        if not urls:
            raise ValidationError('At least one URL is required')
        
        validator = URLValidator()
        valid_urls = []
        
        for i, url in enumerate(urls, 1):
            try:
                validator(url)
                parsed = urlparse(url)
                if parsed.scheme not in ['http', 'https']:
                    raise ValidationError(f'Line {i}: Only HTTP/HTTPS URLs are supported')
                valid_urls.append(url)
            except Exception as e:
                raise ValidationError(f'Line {i}: Invalid URL "{url}" - {str(e)}')
        
        return valid_urls


class JobFilterForm(forms.Form):
    """Form for filtering scraping jobs."""
    
    STATUS_CHOICES = [('', 'All Statuses')] + list(ScrapingJob.STATUS_CHOICES)
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    domain = forms.ModelChoiceField(
        queryset=Domain.objects.all(),
        required=False,
        empty_label='All Domains',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search jobs...'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
