// Globals for apartment selection and payment
let currentShax = [];
let currentJkName = '';
let currentBlock = '';
let userSelection = {};
const allowedHybridProjects = ['ЖК_Рассвет', 'ЖК_Бахор'];


  // 1) Открыть модалку и загрузить список ЖК
  async function openAttachModal() {
    userSelection = {};
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
    // Используем количество комнат из API, если нет - берем из исходных данных шахматки
    info.roomsCount = info.roomsCount || r[3] || 1;
    // Используем тип помещения из API, если нет - берем из исходных данных шахматки (r[1])
    info.unitType = info.unitType || (r.length > 1 ? r[1] : null) || null;
    initializeUserSelection(info);
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
function initializeUserSelection(info) {
  userSelection = {
    jkName: currentJkName,
    block: currentBlock,
    floor: info.floor,
    number: info.apartment_number,
    apartmentSize: info.size,
    roomsCount: info.roomsCount,
    unitType: info.unitType || null,  // Сохраняем тип помещения
    paymentType: null,
    pricePerM2: null,
    totalPrice: null,
    percent: null,
    initialPayment: null,
    monthlyPayment: null,
    hybridLastPayment: null,
    termMonths: info.months_left || null,
    currency: 'UZS'
  };
}

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
  initializeUserSelection(info);

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
    const existingHybrid = resultContainer.querySelector('.hybrid-options');
    if (existingHybrid) existingHybrid.remove();

    // вычисляем стоимость при полной оплате
    const sizeNum = parseFloat(String(userSelection.apartmentSize).replace(',', '.')) || 0;
    const fullPrice = pricePerM2_100 * sizeNum;
    const economy = total_price - fullPrice;
    userSelection.paymentType = 'full';
    userSelection.totalPrice = fullPrice;
    userSelection.pricePerM2 = pricePerM2_100;
    userSelection.percent = "100"
    userSelection.initialPayment = fullPrice;
    userSelection.monthlyPayment = 0;
    userSelection.termMonths = 0;
    userSelection.hybridLastPayment = 0;
    userSelection.paymentChoice = 100;
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
    const existingPerc = buttonsContainer.querySelector('.installment-options');
    if (existingPerc) existingPerc.remove();
    const existingHybrid = resultContainer.querySelector('.hybrid-options');
    if (existingHybrid) existingHybrid.remove();
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
        userSelection.percent = "30"
        if (percent === 70) priceM2 = pricePerM2_70, userSelection.percent = "70";
        if (percent === 50) priceM2 = pricePerM2_50,  userSelection.percent = "50";
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
        userSelection.termMonths = months_left || months;
        userSelection.monthlyPayment = Math.round(monthly);
        userSelection.hybridLastPayment = null;
        userSelection.paymentChoice = percent;
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

  // Показываем гибридную рассрочку для всех проектов
  // if (allowedHybridProjects.includes(currentJkName)) {
    const hybridButton = document.createElement('button');
    hybridButton.textContent = 'Гибридная';
    hybridButton.className = 'payment-option-btn';
    hybridButton.addEventListener('click', () => {
      resultContainer.innerHTML = '';
      const existingInstallments = buttonsContainer.querySelector('.installment-options');
      if (existingInstallments) existingInstallments.remove();

      const hybridOptions = document.createElement('div');
      hybridOptions.className = 'hybrid-options';
      hybridOptions.style.display = 'flex';
      hybridOptions.style.gap = '5px';
      hybridOptions.style.marginBottom = '10px';

      const sizeNum = parseFloat(String(userSelection.apartmentSize).replace(',', '.')) || 0;

      [30, 20].forEach(initialPct => {
        const hybridPctBtn = document.createElement('button');
        hybridPctBtn.textContent = `${initialPct}%`;
        hybridPctBtn.className = 'hybrid-percent-btn';
        hybridPctBtn.addEventListener('click', () => {
          const totalPrice = pricePerM2_30 * sizeNum;
          const initialPayment = totalPrice * (initialPct / 100);
          const lastPaymentPercent = 30;
          const lastPayment = totalPrice * (lastPaymentPercent / 100);
          const months = months_left > 0 ? months_left : 1;
          const middleMonths = months > 1 ? months - 1 : 1;
          const middleTotal = totalPrice - initialPayment - lastPayment;
          const monthlyPayment = middleMonths > 0 ? middleTotal / middleMonths : 0;

          userSelection.paymentType = 'hybrid';
          userSelection.pricePerM2 = pricePerM2_30;
          userSelection.totalPrice = totalPrice;
          userSelection.initialPayment = initialPayment;
          userSelection.monthlyPayment = Math.round(monthlyPayment);
          userSelection.hybridLastPayment = Math.round(lastPayment);
          userSelection.termMonths = months;
          userSelection.percent = `Гибридная ${initialPct}% + ${lastPaymentPercent}%`;
          userSelection.paymentChoice = `hybrid-${initialPct}`;

          const monthlyLabel = middleMonths > 0
            ? `<p>Ежемесячно (первые ${middleMonths} мес.): ${Math.round(monthlyPayment).toLocaleString('ru-RU')} сум</p>`
            : '<p>Ежемесячная оплата не требуется.</p>';

          resultContainer.innerHTML = `
            <p><strong>Гибридная рассрочка (${initialPct}% + ${lastPaymentPercent}%):</strong></p>
            <p>Стоимость: ${Math.round(totalPrice).toLocaleString('ru-RU')} сум</p>
            <p>Первоначальный взнос (${initialPct}%): ${Math.round(initialPayment).toLocaleString('ru-RU')} сум</p>
            ${monthlyLabel}
            <p>Последний платёж (${months}-й месяц, ${lastPaymentPercent}%): ${Math.round(lastPayment).toLocaleString('ru-RU')} сум</p>
          `;

          document.querySelectorAll('.hybrid-percent-btn').forEach(btn => btn.classList.remove('active'));
          hybridPctBtn.classList.add('active');
        });

        hybridOptions.appendChild(hybridPctBtn);
      });

      resultContainer.appendChild(hybridOptions);
      document.querySelectorAll('.payment-option-btn').forEach(b => b.classList.remove('active'));
      hybridButton.classList.add('active');
    });

    buttonsContainer.appendChild(hybridButton);
  // }

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
      await attachApartment();
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
    if (!userSelection.paymentType) {
      alert('Пожалуйста, выберите способ оплаты перед закреплением квартиры.');
      return;
    }
    const leadId = document.getElementById('attach-lead-id').value;
    const squareMeters = parseFloat(String(userSelection.apartmentSize).replace(',', '.')) || null;
    const roomsCount = userSelection.roomsCount || null;
    const totalPrice = typeof userSelection.totalPrice === 'number' ? Math.round(userSelection.totalPrice) : null;
    const pricePerM2 = typeof userSelection.pricePerM2 === 'number' ? Math.round(userSelection.pricePerM2) : null;
    const downPayment = typeof userSelection.initialPayment === 'number' ? Math.round(userSelection.initialPayment) : null;

    if (!totalPrice || !pricePerM2) {
      alert('Не удалось определить стоимость квартиры. Повторите выбор квартиры.');
      return;
    }

    let paymentTypeLabel = 'Единовременно';
    let monthlyPaymentValue = null;
    let installmentPeriodValue = null;

    if (userSelection.paymentType === 'installment') {
      if (downPayment === null) {
        alert('Пожалуйста, выберите процент рассрочки.');
        return;
      }
      paymentTypeLabel = 'Рассрочка';
      installmentPeriodValue = userSelection.termMonths || null;
      monthlyPaymentValue = typeof userSelection.monthlyPayment === 'number'
        ? Math.round(userSelection.monthlyPayment)
        : null;
      if (monthlyPaymentValue === null) {
        alert('Пожалуйста, выберите процент рассрочки.');
        return;
      }
    } else if (userSelection.paymentType === 'hybrid') {
      if (downPayment === null || typeof userSelection.hybridLastPayment !== 'number') {
        alert('Пожалуйста, выберите параметры гибридной рассрочки.');
        return;
      }
      paymentTypeLabel = 'Гибридная рассрочка';
      installmentPeriodValue = userSelection.termMonths || null;
      monthlyPaymentValue = typeof userSelection.monthlyPayment === 'number'
        ? Math.round(userSelection.monthlyPayment)
        : null;
      if (monthlyPaymentValue === null) {
        alert('Пожалуйста, выберите параметры гибридной рассрочки.');
        return;
      }
    }

    try {
      const res = await fetch(`/api/leads/${leadId}/attach-apartment`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
            square_meters: squareMeters ?? userSelection.apartmentSize,
            rooms: roomsCount ?? userSelection.roomsCount,
            floor: userSelection.floor,
            total_price: totalPrice,
            currency: userSelection.currency || 'UZS',
            payment_type: paymentTypeLabel,
            monthly_payment: monthlyPaymentValue,
            installment_period: installmentPeriodValue,
            complex_name: currentJkName,
            number_apartments: userSelection.number,
            block: currentBlock,
            down_payment: downPayment,
            square_meters_price: pricePerM2,
            down_payment_percent: userSelection.percent,
            unit_type: userSelection.unitType || null
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
