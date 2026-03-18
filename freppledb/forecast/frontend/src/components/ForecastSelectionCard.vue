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
import {useForecastsStore} from "@/stores/forecastsStore";

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

const preferences = computed(() => store.preferences);
const data = computed(() => (props.panelid === 'I') ? store.itemTree: (props.panelid === 'L') ? store.locationTree: store.customerTree);
const modelName = (props.panelid === 'I') ? 'item': (props.panelid === 'L') ? 'location': 'customer';
const currentHeight = computed(() => (store.dataRowHeight || 240));

function selectILCobject(model, rowIndex) {
  store.setItemLocationCustomer(model, {Name: data.value[rowIndex][model], Description: data.value[rowIndex]['description']}, data.value[rowIndex]['children'], data.value[rowIndex]['lvl'],data.value[rowIndex].expanded === 0);
  if (data.value[rowIndex]['children']) {
    toggleRowVisibility(rowIndex);
  }

}

function toggleRowVisibility(rowIndex) {
  // Should this be moved to the store? We are manipulating store values directly.
  data.value[rowIndex].expanded = data.value[rowIndex].expanded === 1 ? 0 : 1;
  const isExpanded = data.value[rowIndex].expanded === 1;
  let lineCount = 0;
  for (let i = rowIndex+1; i < data.value.length; i++) {
    if (data.value[i].lvl < data.value[rowIndex].lvl+1) break;
    if ((data.value[i].lvl > data.value[rowIndex].lvl+1) && isExpanded) continue;
    if (isExpanded) {
      data.value[i].visible = isExpanded;
    } else {
      lineCount++;
    }
  }
  if (lineCount > 0) {
    // data is in sync with the store... this splice will change the tree data in the store
    data.value.splice(rowIndex+1, lineCount);
  }
}

</script>

<template>
  <div class="card selection-card" :style="{'height':  currentHeight - 31 + 'px'}" style="min-height: 100px; max-height: 50vh" :id="modelName + 'panel'">
    <div class="card-header selection-card-header">
      <h5 class="card-title text-capitalize mb-0" translate="">
        <span class="header-icon fa" :class="modelName === 'item' ? 'fa-cube' : modelName === 'location' ? 'fa-map-marker' : 'fa-user'"></span>
        <span>{{ ttt(modelName) }}</span>
      </h5>
    </div>
    <div class="card-body ps-0 pe-0 pt-2 pb-2" style="overflow: auto">
      <div class="">
        <div :id="modelName + 'table'">
          <div class="d-flex w-100 bucket-header-row">
            <div class="w-100 d-flex justify-content-end text-start">
              <span v-for="bucketname in store.treeBuckets" :key="bucketname" class="numbervalues bucket-label">
                <strong><small>{{ bucketname }}</small></strong>
              </span>
            </div>
          </div>

          <div v-for="(row, index) in data" :key="row[modelName]" :class="(row[modelName] === store[modelName].Name) ? 'bg-light active-row' : ''" class="d-flex evtitemrow tree-row" v-on:click="selectILCobject(modelName, index)">
            <div class="overflow-hidden text-nowrap me-3" :style="'padding-left: ' + row.lvl * 13 + 'px'" data-bs-toggle="tooltip" :data-bs-title="row['description']">
              &nbsp;<span v-if="row.children && row.visible" class="fa tree-toggle" :class="row.expanded === 1 ? 'fa-caret-down' : 'fa-caret-right'"></span>
              {{ row.visible ? row[modelName] : '' }}
              <template v-if="store.showDescription && row['description']">
                &nbsp;-&nbsp;{{ row["description"] }}
              </template>
            </div>
            <div v-if="row.visible" class="ms-auto d-flex justify-content-end text-start">
              <span v-for="val in row.values" :key="val.bucketname" class="numbervalues">{{val.value}}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.selection-card {
  transition: box-shadow 0.2s ease;
}

.selection-card-header {
  display: flex;
  align-items: center;
}

.header-icon {
  margin-right: 6px;
  font-size: 0.8rem;
  opacity: 0.85;
}

.bucket-header-row {
  padding: 2px 15px 4px;
  border-bottom: 1px solid #F3E8FF;
  margin-bottom: 2px;
}

.bucket-label strong small {
  color: #7B2D8E;
  font-size: 0.72rem;
  letter-spacing: 0.2px;
}

.tree-row {
  padding: 2px 15px 3px !important;
  border-radius: 4px;
  margin: 0 4px;
  font-size: 0.82rem;
}

.tree-toggle {
  color: #7B2D8E;
  font-size: 0.85rem;
}

.active-row {
  background-color: rgba(123, 45, 142, 0.08) !important;
  border-left: 3px solid #7B2D8E;
  font-weight: 500;
}
</style>
