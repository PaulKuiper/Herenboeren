import {Component, Prop, State} from '@stencil/core';


@Component({
    tag: 'hb-login',
    styleUrl: 'hb-login.scss'
})
export class AppHome {
    @Prop({context: 'i18n'}) private i18n: any;

    @State() private lang: string;

    changeLang() {
        if (this.i18n.language === 'nl') {
            this.i18n.changeLanguage('en');
            document.documentElement.style.setProperty('--ion-color-primary', 'red');
        } else {
            this.i18n.changeLanguage('nl');
            document.documentElement.style.setProperty('--ion-color-primary', 'green');
        }
        this.lang = this.i18n.language;
    }

    componentWillLoad() {
        this.lang = this.i18n.language;
    }

    render() {
        return [
            <ion-card>
                <ion-card-content>
                    <ion-card-title>{this.i18n.t("auth.login")}</ion-card-title>

                    <form>
                        <ion-row>
                            <ion-col>
                                <ion-list>

                                    <ion-item>
                                        <ion-label>{this.i18n.t("auth.email")}</ion-label>
                                        <ion-input type="email" name="email" required></ion-input>
                                    </ion-item>

                                    <ion-item>
                                        <ion-label>{this.i18n.t("auth.password")}</ion-label>
                                        <ion-input type="password" name="password" required></ion-input>
                                    </ion-item>

                                </ion-list>
                            </ion-col>
                        </ion-row>
                        <div id="spacer"></div>
                        <ion-row>
                            <ion-col>
                                <ion-button type="submit">{this.i18n.t("auth.login")}</ion-button>
                                <ion-button>{this.i18n.t("auth.registration")}</ion-button>
                            </ion-col>
                        </ion-row>
                    </form>
                    <a onClick={() => this.changeLang()}>{this.lang.toUpperCase()}</a>
                </ion-card-content>
            </ion-card>
        ];
    }
}
