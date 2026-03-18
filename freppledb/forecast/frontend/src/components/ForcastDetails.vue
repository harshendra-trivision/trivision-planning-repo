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

<script setup lang="js">
import {computed} from "vue";
import { useI18n } from 'vue-i18n';
import { useForecastsStore } from '@/stores/forecastsStore';
import AttributesTab from './AttributesTab.vue';
import ForecastTab from './ForecastTab.vue';
import CommentsTab from './CommentsTab.vue';

const { t: ttt, locale, availableLocales } = useI18n({
  useScope: 'global',  // This is crucial for reactivity
  inheritLocale: true
});

const store = useForecastsStore();

const database = computed(() => window.database);

function save() {
  if (store.hasChanges) store.saveForecastChanges();
}

function undo() {
  if (store.hasChanges) {
    store.undo();
  }
}
</script>

<template>
  <div class="details-wrapper">
    <div class="row align-items-center details-toolbar">
      <div class="col-auto">
        <div class="form-inline d-flex gap-1">
          <button
              id="save"
              class="btn btn-primary me-1 text-capitalize action-btn"
              @click="save(false)"
              data-bs-toggle="tooltip"
              :disabled="!store.hasChanges"
              :class="store.hasChanges ? 'btn-danger has-changes' : ''"
              :data-bs-original-title="ttt('Save changes')">
            <span class="fa fa-check me-1" v-if="store.hasChanges"></span>
            {{ ttt('save') }}
          </button>
          <button
              id="undo"
              class="btn btn-primary text-capitalize action-btn"
              @click="undo()"
              data-bs-toggle="tooltip"
              :disabled="!store.hasChanges"
              :class="store.hasChanges ? 'btn-danger has-changes' : ''"
              :data-bs-original-title="ttt('Undo changes')">
            <span class="fa fa-undo me-1" v-if="store.hasChanges"></span>
            {{ ttt('Undo') }}
          </button>
        </div>
      </div>

      <div class="col">
        <h1 class="d-inline detail-title" v-for="(model, index) in store.currentSequence" :key="model">
          <span v-if="index > 0" class="title-separator">&nbsp;-&nbsp;</span>
          <span v-if="model==='I'" class="title-item">{{ store.item.Name }}{{ store.item.Description ? " (" + store.item.Description + ")" : "" }}
          <a :href="'/' + database + '/detail/input/item/' + store.item.Name + '/'" onclick.stop="" class="detail-link"><span class="fa fa-caret-right"></span></a>
        </span>
          <span v-if="model==='L'" class="title-item">{{ store.location.Name }}{{ store.location.Description ? " (" + store.location.Description + ")" : ""}}
          <a :href="'/' + database + '/detail/input/location/' + store.location.Name + '/'" onclick.stop="" class="detail-link"><span class="fa fa-caret-right"></span></a>
        </span>
          <span v-if="model==='C'" class="title-item">{{ store.customer.Name }}{{ store.customer.Description ?  " (" + store.customer.Description + ")" : "" }}
          <a :href="'/' + database + '/detail/input/customer/' + store.customer.Name + '/'" onclick.stop="" class="detail-link"><span class="fa fa-caret-right"></span></a>
        </span>
        </h1>
      </div>

      <div id="tabs" class="col-auto form-inline">
        <ul class="nav nav-tabs modern-tabs">
          <li class="nav-item" id="attributestab" role="presentation" @click="store.setShowTab('attributes')">
            <a :class="['text-capitalize', {'nav-link': true, 'active': store.showTab === 'attributes'}]" class="text-capitalize nav-link">
              <span>{{ ttt('attributes') }}</span>
            </a>
          </li>
          <li class="nav-item" id="forecasttab" role="presentation" @click="store.setShowTab('forecast')">
            <a :class="['text-capitalize', {'nav-link': true, 'active': store.showTab === 'forecast'}]" class="text-capitalize nav-link">
              <span>{{ ttt('forecast') }}</span>
            </a>
          </li>
          <li class="nav-item" id="commentstab" role="presentation" @click="store.setShowTab('comments')">
            <a :class="['text-capitalize', {'nav-link': true, 'active': store.showTab === 'comments'}]" class="text-capitalize nav-link">
              <span>{{ ttt('comments') }}</span>
            </a>
          </li>
        </ul>
      </div>
    </div>

    <div class="tab-content mt-3 mb-3">
      <AttributesTab v-if="store.showTab === 'attributes'" />
      <ForecastTab v-if="store.showTab === 'forecast'" />
      <CommentsTab v-if="store.showTab === 'comments'" />
    </div>
  </div>
</template>

<style scoped>
.details-wrapper {
  background: #FFFFFF;
  border-radius: 12px;
  border: 1px solid #E8E0F0;
  padding: 0.75rem 1rem;
  box-shadow: 0 2px 12px rgba(45, 0, 77, 0.04);
}

.details-toolbar {
  padding-bottom: 0.5rem;
}

.action-btn {
  font-size: 0.82rem !important;
  min-width: 70px;
}

.has-changes {
  animation: pulse-attention 2s ease-in-out infinite;
}

@keyframes pulse-attention {
  0%, 100% { box-shadow: 0 2px 6px rgba(239, 68, 68, 0.2); }
  50% { box-shadow: 0 2px 12px rgba(239, 68, 68, 0.4); }
}

.detail-title {
  font-size: 1rem !important;
  font-weight: 600;
  color: #2D004D;
}

.title-separator {
  color: #C4B5D0;
}

.title-item {
  color: #1A1A1A;
}

.detail-link {
  color: #7B2D8E;
  text-decoration: none;
  transition: color 0.15s ease;
}

.detail-link:hover {
  color: #A855F7;
}

.modern-tabs {
  border-bottom: 2px solid #F3E8FF !important;
}

.modern-tabs .nav-link {
  cursor: pointer;
  border: none !important;
  padding: 0.45rem 0.9rem !important;
  font-size: 0.82rem;
}
</style>
