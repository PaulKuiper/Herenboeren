/*
  This is temporarily commented out as the `setupConfig` method has been temporarily removed
*/

// import { setupConfig } from '@ionic/core';

//setupConfig({
  // uncomment the following line to force mode to be Material Design
  // mode: 'md'
//});

import {i18n} from './translation';

declare var Context: any;

Context.i18n = i18n;