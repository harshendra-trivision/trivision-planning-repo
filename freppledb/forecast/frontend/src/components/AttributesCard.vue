/*
 * Copyright (C) 2025 by frePPLe bv
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
 * LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
 * WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
 */

<script setup>
import { useI18n } from 'vue-i18n';
import {useForecastsStore} from "@/stores/forecastsStore.js";

const { t: ttt, locale, availableLocales } = useI18n({
  useScope: 'global',  // This is crucial for reactivity
  inheritLocale: true
});

const store = useForecastsStore();

const props = defineProps({
  panelid: {
    type: String,
    default: null
  }
});
const modelName = (props.panelid === 'I') ? 'item': (props.panelid === 'L') ? 'location': 'customer';
</script>

<template>
  <div class="card attributes-card">
    <div class="card-header">
      <h5 class="card-title text-capitalize mb-0" translate="">
        <span class="fa me-1" :class="modelName === 'item' ? 'fa-cube' : modelName === 'location' ? 'fa-map-marker' : 'fa-user'" style="font-size: 0.8rem; opacity: 0.85;"></span>
        <span class="">{{ ttt(modelName) }}</span>
      </h5>
    </div>
    <div class="card-body">
      <div class="table-responsive">
        <table class="table table-borderless table-sm table-hover">
          <tbody>
            <tr v-for="(value, key) in store[modelName]" :key="key">
              <td v-if="key === 'Name' && (locale === 'en' || locale === 'de')" class="attr-label">{{ key }}:</td>
              <td v-if="key === 'Name' && (locale === 'en' || locale === 'de')" class="attr-value">{{value}}</td>
              <td v-if="key !== 'Name'" class="attr-label">{{ key }}:</td>
              <td v-if="key !== 'Name'" class="attr-value">{{value}}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.attributes-card {
  transition: box-shadow 0.2s ease;
}

.attr-label {
  width: 100px;
  white-space: nowrap;
  font-weight: 500 !important;
  color: #6B7280 !important;
  font-size: 0.82rem !important;
}

.attr-value {
  font-size: 0.82rem !important;
  color: #1A1A1A !important;
}
</style>
