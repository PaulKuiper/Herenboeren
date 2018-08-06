import '@ionic/core';
import { Component, Prop, Listen } from '@stencil/core';

@Component({
  tag: 'hb-app',
  styleUrl: 'hb-app.scss'
})
export class HbApp {

  @Prop({ connect: 'ion-toast-controller' }) toastCtrl: HTMLIonToastControllerElement;

  /**
   * Handle service worker updates correctly.
   * This code will show a toast letting the
   * user of the PWA know that there is a
   * new version available. When they click the
   * reload button it then reloads the page
   * so that the new service worker can take over
   * and serve the fresh content
   */
  @Listen('window:swUpdate')
  async onSWUpdate() {
    const toast = await this.toastCtrl.create({
      message: 'New version available',
      showCloseButton: true,
      closeButtonText: 'Reload'
    });
    await toast.present();
    await toast.onWillDismiss();
    window.location.reload();
  }

  render() {
    return (
      <ion-app>
        <ion-router useHash={false}>
          <ion-route url='/' component='hb-home'></ion-route>
          <ion-route url='/login' component='hb-login'></ion-route>
        </ion-router>
[

            <ion-menu side="start">
                <ion-header translucent>
                    <ion-toolbar color="secondary">
                        <ion-title>Menu</ion-title>
                    </ion-toolbar>
                </ion-header>
            </ion-menu>
        {/*<ion-nav></ion-nav>*/}
        <ion-router-outlet main></ion-router-outlet>

      </ion-app>
    );
  }
}

