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


class DocumentType(models.TextChoices):
    """
    Enum for different document types supported by the system.
    """
    INVOICE = "invoice", _("Invoice")
    RECEIPT = "receipt", _("Receipt")
    CONTRACT = "contract", _("Contract")
    ID_DOCUMENT = "id_document", _("ID Document")
    PASSPORT = "passport", _("Passport")
    DRIVERS_LICENSE = "drivers_license", _("Driver's License")
    BANK_STATEMENT = "bank_statement", _("Bank Statement")
    HR_FORM = "hr_form", _("HR Form")
    MEDICAL_RECORD = "medical_record", _("Medical Record")
    TAX_FORM = "tax_form", _("Tax Form")
    LEGAL_DOCUMENT = "legal_document", _("Legal Document")
    CERTIFICATE = "certificate", _("Certificate")
    LETTER = "letter", _("Letter")
    REPORT = "report", _("Report")
    FORM = "form", _("Form")
    OTHER = "other", _("Other")


class ProcessingStatus(models.TextChoices):
    """
    Enum for document processing status.
    """
    PENDING = "pending", _("Pending")
    PROCESSING = "processing", _("Processing")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
