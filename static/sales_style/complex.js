// Globals for apartment selection and payment
let currentShax = [];
let currentJkName = '';
let currentBlock = '';
let userSelection = {};


  // 1) Открыть модалку и загрузить список ЖК
  async function openAttachModal() {
    document.getElementById('attachModal').style.display = 'flex';

    // Сбросим предыдущие шаги
    document.getElementById('attach-blocks').innerHTML = '';
    document.getElementById('attach-apartments').innerHTML = '';

    const jkSelect = document.getElementById('attach-jk-select');
    jkSelect.disabled = true;
    jkSelect.innerHTML = '<option>Загрузка...</option>';

    try {
      // Правильный эндпоинт — /api/complexes/
      const res = await fetch('/api/complexes/');
      const json = await res.json();
      const list = json.complexes || [];

      jkSelect.innerHTML = '<option value="">-- выберите ЖК --</option>';
      list.forEach(jk => {
        const opt = document.createElement('option');
        opt.value = jk.name;      // у вас в бэке name — это ключ ЖК
        opt.textContent = jk.name;
        jkSelect.appendChild(opt);
      });
      jkSelect.disabled = false;
    } catch (e) {
      jkSelect.innerHTML = '<option>Ошибка загрузки ЖК</option>';
    }
  }

  // 2) Закрыть модалку
  function closeAttachModal() {
    document.getElementById('attachModal').style.display = 'none';
  }

  // 3) При смене ЖК — подгрузить шахматку
  document.getElementById('attach-jk-select')
    .addEventListener('change', async function() {
      const jkName = this.value;
      const blocksContainer = document.getElementById('attach-blocks');
      blocksContainer.innerHTML = '';
      document.getElementById('attach-apartments').innerHTML = '';

      if (!jkName) return;

      try {
        // Роут /api/complexes/jk/{jk_name}
        const res = await fetch(`/api/complexes/jk/${encodeURIComponent(jkName)}`);
        const data = await res.json();
        const shax = data.shaxmatka || [];
        currentShax = shax;
        currentJkName = jkName;

        // Список блоков
        const unique = [...new Set(shax.map(r => r[0]))];
        unique.forEach(block => {
          const btn = document.createElement('button');
          btn.className = 'block-button';
          btn.textContent = block;
          btn.addEventListener('click', () => {
            // визуальная отметка
            blocksContainer.querySelectorAll('.block-button')
              .forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentBlock = block;
            renderApartments(shax, jkName, block);
          });
          blocksContainer.appendChild(btn);
        });
      } catch (e) {
        blocksContainer.innerHTML = '<p>Не удалось загрузить блоки.</p>';
      }
    });

  // 4) Построить шахматку квартир
  function renderApartments(shaxmatkaData, jkName, block) {
    const container = document.getElementById('attach-apartments');
    container.innerHTML = '';
  
    // Группируем по этажам
    const floorsMap = shaxmatkaData
      .filter(r => r[0] === block)
      .reduce((acc, r) => {
        const fl = Number(r[6]);
        if (!acc[fl]) acc[fl] = [];
        acc[fl].push(r);
        return acc;
      }, {});
  
    // Сортируем этажи по убыванию
    const sortedFloors = Object.keys(floorsMap)
      .map(Number)
      .sort((a, b) => b - a);
  
    sortedFloors.forEach(floor => {
      // Обёртка этажа
      const floorDiv = document.createElement('div');
      floorDiv.className = 'floor-row';
  
      // Метка этажа
      const label = document.createElement('div');
      label.className = 'floor-label';
      label.textContent = `${floor} этаж`;
      floorDiv.appendChild(label);
  
      // Ряд квартир
      const row = document.createElement('div');
      row.className = 'apt-row';
  
      floorsMap[floor].forEach(r => {
        const status = r[2].trim().toLowerCase();
        const card = document.createElement('div');
        card.className = `apt-card ${
          status === 'свободна' ? 'available'
          : status === 'продана'  ? 'sold'
          : 'booked'
        }`;
        // Compute display values
        const sizeValue = r[5] || '-';
        const priceValue = (status === 'свободна' && r.length > 7 && r[7])
          ? Number(r[7]).toLocaleString('ru-RU') + ' сум'
          : r[2];
        // Build card inner HTML
        card.innerHTML = `
          <div class="apt-card-header">
            <span>№${r[4] || '—'}</span>
          </div>
          <div class="apt-card-body">
            <span class="apt-size">${sizeValue} м²</span> <br>
            <span class="apt-price">${priceValue}</span>
          </div>
        `;
  
      if (status === 'свободна') {
        card.addEventListener('click', () => {
          fetchAndShowPaymentOptions(r);
        });
      }
  
        row.appendChild(card);
      });
  
      floorDiv.appendChild(row);
      container.appendChild(floorDiv);
    });

    // Equalize all apartment card widths to match the widest card
    requestAnimationFrame(() => {
      const cards = container.querySelectorAll('.apt-row .apt-card');
      let maxWidth = 0;
      cards.forEach(card => {
        maxWidth = Math.max(maxWidth, card.offsetWidth);
      });
      cards.forEach(card => {
        card.style.minWidth = maxWidth + 'px';
      });
    });
  }


/**
 * Загружает данные квартиры с сервера и вызывает showPaymentOptions.
 * @param {Array} r - исходная запись шахматки.
 */
async function fetchAndShowPaymentOptions(r) {
  try {
    const params = new URLSearchParams({
      jkName: currentJkName,
      blockName: currentBlock,
      apartmentSize: r[5],
      floor: r[6],
      apartmentNumber: r[4]
    });
    console.log({
      jkName: currentJkName,
      blockName: currentBlock,
      apartmentSize: r[5],
      floor: r[6],
      apartmentNumber: r[4]
    });
    const res = await fetch(`/api/complexes/apartment-info?${params.toString()}`);
    if (!res.ok) throw new Error('Ошибка загрузки данных квартиры');
    const json = await res.json();
    if (json.status !== 'success') {
      throw new Error(json.detail || 'Некорректный ответ сервера');
    }
    const info = json.data;
    // Добавляем недостающие поля из r
    info.roomsCount = 1;
    showPaymentOptions(info);
  } catch (e) {
    alert(e.message);
  }
}

/**
 * Отображает выбор способа оплаты для выбранной квартиры,
 * затем на «Выбрать» заполняет основную форму и закрывает модалку.
 * @param {Object} info - объект с данными квартиры, где:
 *   info.floor, info.apartment_number, info.size, info.roomsCount,
 *   info.pricePerM2_100, info.pricePerM2_70, info.pricePerM2_50, info.pricePerM2_30,
 *   info.total_price, info.months_left
 */
function showPaymentOptions(info) {
  const container = document.getElementById('attach-apartments');
  container.innerHTML = '';

  const pricePerM2_100 = info.pricePerM2_100;
  const pricePerM2_70 = info.pricePerM2_70;
  const pricePerM2_50 = info.pricePerM2_50;
  const pricePerM2_30 = info.pricePerM2_30;
  const total_price = info.total_price;
  const months_left = info.months_left;

  // Сохраняем базовые данные выбора
  userSelection.jkName = currentJkName;
  userSelection.block = currentBlock;
  userSelection.floor = info.floor;
  userSelection.number = info.apartment_number;
  userSelection.apartmentSize = info.size;
  userSelection.roomsCount = info.roomsCount;

  // Контейнеры для кнопок и результата
  const buttonsContainer = document.createElement('div');
  buttonsContainer.className = 'buttons-container';
  const resultContainer = document.createElement('div');
  resultContainer.className = 'result-container';
  resultContainer.style.margin = '10px 0';

  // 1) Кнопка 100% Оплата
  const fullPaymentBtn = document.createElement('button');
  fullPaymentBtn.textContent = '100% Оплата';
  fullPaymentBtn.className = 'payment-option-btn';
  fullPaymentBtn.addEventListener('click', () => {
    // Remove any existing installment options
    const existingPerc = buttonsContainer.querySelector('.installment-options');
    if (existingPerc) existingPerc.remove();

    // вычисляем стоимость при полной оплате
    const sizeNum = parseFloat(String(userSelection.apartmentSize).replace(',', '.')) || 0;
    const fullPrice = pricePerM2_100 * sizeNum;
    const economy = total_price - fullPrice;
    userSelection.paymentType = 'full';
    userSelection.totalPrice = fullPrice;
    userSelection.pricePerM2 = pricePerM2_100;
    // updateInitialPayment(fullPrice); // Removed as per instructions
    userSelection.termMonths = 0;
    resultContainer.innerHTML = `
      <p><strong>Стоимость (100%):</strong> ${fullPrice.toLocaleString('ru-RU')} сум</p>
      ${economy > 0 ? `<p><strong>Экономия:</strong> ${economy.toLocaleString('ru-RU')} сум</p>` : ''}
    `;
    document.querySelectorAll('.payment-option-btn').forEach(b => b.classList.remove('active'));
    fullPaymentBtn.classList.add('active');
  });
  buttonsContainer.appendChild(fullPaymentBtn);

  // 2) Кнопка Рассрочка (открывает выбор процента)
  const installmentBtn = document.createElement('button');
  installmentBtn.textContent = 'Рассрочка';
  installmentBtn.className = 'payment-option-btn';
  installmentBtn.addEventListener('click', () => {
    resultContainer.innerHTML = ''; // очищаем предыдущее
    const percContainer = document.createElement('div');
    percContainer.className = 'installment-options';
    percContainer.style.display = 'flex';
    percContainer.style.gap = '5px';
    percContainer.style.marginBottom = '10px';

    [70, 50, 30].forEach(percent => {
      const pctBtn = document.createElement('button');
      pctBtn.textContent = `${percent}%`;
      pctBtn.className = 'installment-percent-btn';
      pctBtn.addEventListener('click', () => {
        // расчет при выбранном проценте
        const sizeNum = parseFloat(String(userSelection.apartmentSize).replace(',', '.')) || 0;
        let priceM2 = pricePerM2_30; // по умолчанию
        if (percent === 70) priceM2 = pricePerM2_70;
        if (percent === 50) priceM2 = pricePerM2_50;
        const totalR = priceM2 * sizeNum;
        const initial = totalR * (percent / 100);
        const remaining = totalR - initial;
        const months = userSelection.termMonths || months_left || 1;
        const monthly = remaining / months;
        const econ = total_price - totalR;

        userSelection.paymentType = 'installment';
        userSelection.pricePerM2 = priceM2;
        userSelection.totalPrice = totalR;
        userSelection.initialPayment = initial;
        userSelection.termMonths = months_left;
        resultContainer.innerHTML = `
          <p><strong>Рассрочка (${percent}%):</strong></p>
          <p>Стоимость: ${totalR.toLocaleString('ru-RU')} сум</p>
          <p>Первый взнос: ${initial.toLocaleString('ru-RU')} сум</p>
          <p>Ежемесячно (${months} мес.): ${Math.round(monthly).toLocaleString('ru-RU')} сум</p>
          ${econ > 0 ? `<p><strong>Экономия:</strong> ${econ.toLocaleString('ru-RU')} сум</p>` : ''}
        `;
        document.querySelectorAll('.installment-percent-btn').forEach(b => b.classList.remove('active'));
        pctBtn.classList.add('active');
      });
      percContainer.appendChild(pctBtn);
    });

    buttonsContainer.appendChild(percContainer);
    document.querySelectorAll('.payment-option-btn').forEach(b => b.classList.remove('active'));
    installmentBtn.classList.add('active');
  });
  buttonsContainer.appendChild(installmentBtn);

  // 3) Контрольные кнопки «Назад» и «Выбрать»
  const control = document.createElement('div');
  control.className = 'control-buttons';
  const backBtn = document.createElement('button');
  backBtn.textContent = 'Назад';
  backBtn.addEventListener('click', () => renderApartments(currentShax, currentJkName, currentBlock));
  const chooseBtn = document.createElement('button');
  chooseBtn.textContent = 'Выбрать';
  chooseBtn.addEventListener('click', async () => {
    try {
      await attachApartment(
        userSelection.jkName,
        userSelection.block,
        userSelection.floor,
        userSelection.number
      );
      // Page will reload on successful attachApartment call
    } catch (e) {
      alert('Ошибка: не удалось закрепить квартиру.');
    }
  });
  control.appendChild(backBtn);
  control.appendChild(chooseBtn);

  // Добавляем все в контейнер
  container.appendChild(buttonsContainer);
  container.appendChild(resultContainer);
  container.appendChild(control);
}




  // 5) Отправить запрос на привязку к лиду
  async function attachApartment() {
    const leadId = document.getElementById('attach-lead-id').value;
    try {
      const res = await fetch(`/api/leads/${leadId}/attach-apartment`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
            square_meters: userSelection.apartmentSize,
            rooms: userSelection.roomsCount,
            floor: userSelection.floor,
            total_price: userSelection.initialPayment,
            currency: userSelection.currency || 'UZS',
            payment_type: userSelection.paymentType === 'full' ? 'Единовременно' : 'Рассрочка',
            monthly_payment: userSelection.pricePerM2 || null,
            installment_period: userSelection.termMonths || null,
          })
      });
      if (!res.ok) throw new Error();
      alert(`Квартира №${userSelection.number} закреплена к лиду.`);
      closeAttachModal();
      location.reload(); // или обновите только часть UI
    } catch (e) {
      alert('Ошибка: не удалось закрепить квартиру.');
    }
  }
