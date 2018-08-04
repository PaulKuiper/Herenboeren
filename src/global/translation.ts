import i18next from "i18next";
import i18nextXHRBackend from 'i18next-xhr-backend'
import i18nextBrowserLanguageDetector from 'i18next-browser-languagedetector'

export const i18n = i18next
        .use(i18nextXHRBackend)
        .use(i18nextBrowserLanguageDetector)
        .init({
            fallbackLng: 'en',
            ns: ['default'],
            defaultNS: 'default',
            backend: {loadPath: 'assets/locales/{{lng}}/{{ns}}.json'},
            initImmediate: false,
            debug: true
        });
