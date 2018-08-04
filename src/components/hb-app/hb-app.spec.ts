import { TestWindow } from '@stencil/core/testing';
import { HbApp } from './hb-app';

describe('my-app', () => {

  it('should update', async () => {
    await window.flush();
  });

  let element: HTMLAppProfileElement;
  let window: TestWindow;
  beforeEach(async () => {
    window = new TestWindow();
    element = await window.load({
      components: [HbApp],
      html: '<my-app></my-app>'
    });
  });
});