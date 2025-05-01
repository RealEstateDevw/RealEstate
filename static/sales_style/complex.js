
  // 1) Открыть модалку и загрузить список ЖК
  async function openAttachModal(leadId) {
    document.getElementById('attach-lead-id').value = leadId;
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
        card.textContent = `№${r[4]}`;
  
        if (status === 'свободна') {
          card.addEventListener('click', () => {
            attachApartment(jkName, block, r[6], r[4]);
          });
        }
  
        row.appendChild(card);
      });
  
      floorDiv.appendChild(row);
      container.appendChild(floorDiv);
    });
  }

  // 5) Отправить запрос на привязку к лиду
  async function attachApartment(jkName, block, floor, number) {
    const leadId = document.getElementById('attach-lead-id').value;
    try {
      const res = await fetch(`/api/leads/${leadId}/attach-apartment`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ jkName, block, floor, number })
      });
      if (!res.ok) throw new Error();
      alert(`Квартира №${number} закреплена к лиду.`);
      closeAttachModal();
      location.reload(); // или обновите только часть UI
    } catch (e) {
      alert('Ошибка: не удалось закрепить квартиру.');
    }
  }
