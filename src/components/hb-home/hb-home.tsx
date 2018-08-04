import {Component} from '@stencil/core';

@Component({
    tag: 'hb-home',
    styleUrl: 'hb-home.scss'
})
export class HbHome {
    render() {
        return (
            <ion-content main>
                <h1>Hello</h1>
                <ion-button href="/login">Login</ion-button>

            </ion-content>
        );
    }
}
