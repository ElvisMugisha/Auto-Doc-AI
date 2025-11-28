from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    SUPER_ADMIN = 'Super_Admin', _('Super Admin')
    ORG_ADMIN = 'Org_Admin', _('Organization Admin')
    TEAM_MEMBER = 'Team_Member', _('Team Member')
    API_CLIENT = 'Api_Client', _('API Client')
    REVIEWER = 'Reviewer', _('Reviewer')
    AUDITOR = 'Auditor', _('Auditor')


class CodeType(models.TextChoices):
    VERIFICATION = 'Email_Verification', _('Email Verification')
    PASSWORD_RESET = 'Password_Reset', _('Password Reset')
    LOGIN_OTP = 'Login_OTP', _('Login OTP')


class Gender(models.TextChoices):
    MALE = 'Male', _('Male')
    FEMALE = 'Female', _('Female')
    OTHER = 'Other', _('Other')


class MaritalStatus(models.TextChoices):
    SINGLE = 'Single', _('Single')
    MARRIED = 'Married', _('Married')
    DIVORCED = 'Divorced', _('Divorced')
    WIDOWED = 'Widowed', _('Widowed')
