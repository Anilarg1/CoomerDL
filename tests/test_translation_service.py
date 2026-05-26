from app.services.translation_service import TranslationService


def test_translation_service_is_english_only():
    service = TranslationService(language="es")

    assert service.language == "en"
    assert service.tr("DOWNLOAD") == "Download"
    assert service.get_available_languages() == [{"code": "en", "name": "English"}]
