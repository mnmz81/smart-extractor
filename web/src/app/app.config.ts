import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideMushiluUi } from '@mushilu-san/ui';

export const appConfig: ApplicationConfig = {
  providers: [provideBrowserGlobalErrorListeners(), provideMushiluUi()],
};
