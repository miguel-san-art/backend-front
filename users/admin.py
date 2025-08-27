# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name = 'Profil'
    verbose_name_plural = 'Profils'
    fk_name = 'user'

class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('email', 'get_full_name', 'get_role', 'is_active', 'is_staff')
    list_filter = ('is_active', 'profile__role')
    search_fields = ('email', 'profile__nom', 'profile__prenom')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    
    def get_full_name(self, obj):
        if hasattr(obj, 'profile'):
            return f"{obj.profile.nom} {obj.profile.prenom}"
        return "-"
    get_full_name.short_description = 'Nom complet'
    
    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return "-"
    get_role.short_description = 'Rôle'

# Enregistrement des modèles dans l'interface d'administration
admin.site.register(User, UserAdmin)
