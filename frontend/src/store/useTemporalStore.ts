import { useStore } from 'zustand';
import { useSwitchStore } from './useSwitchStore';

export function useTemporalStore<T>(
  selector: (state: ReturnType<typeof useSwitchStore.temporal.getState>) => T
) {
  return useStore(useSwitchStore.temporal, selector);
}