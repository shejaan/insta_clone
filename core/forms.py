from django import forms
from .models import Profile, Post, Comment


class ProfileEditForm(forms.ModelForm):
    """Form for editing a user's profile (bio, image, website, privacy)."""

    class Meta:
        model   = Profile
        fields  = ['profile_image', 'bio', 'website', 'private_account']
        widgets = {
            'bio':     forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write a bio...'}),
            'website': forms.URLInput(attrs={'placeholder': 'https://yourwebsite.com'}),
        }


class PostForm(forms.ModelForm):
    """Form for creating a new post with basic file validation."""

    class Meta:
        model  = Post
        fields = ['image', 'caption', 'location']
        widgets = {
            'caption':  forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write a caption...'}),
            'location': forms.TextInput(attrs={'placeholder': 'Add location'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Limit to 10 MB
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Image must be smaller than 10 MB.")
            # Only allow common image types
            allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
            if hasattr(image, 'content_type') and image.content_type not in allowed_types:
                raise forms.ValidationError("Only JPEG, PNG, WebP, and GIF images are allowed.")
        return image


class CommentForm(forms.ModelForm):
    """Minimal inline comment form."""

    class Meta:
        model  = Comment
        fields = ['text']
        widgets = {
            'text': forms.TextInput(attrs={'placeholder': 'Add a comment...', 'autocomplete': 'off'}),
        }
        labels = {'text': ''}
