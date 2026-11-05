const DATA_REQUEST_WAR_ROOM_NAME = "Data Request Coordinator War Room";
const DATA_REQUEST_OVERDUE_SECONDS = 600;

function dataRequestFormatAge(rawSeconds) {
  const seconds = Math.max(0, Math.floor(Number(rawSeconds) || 0));

  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = seconds % 60;

  const two = (value) => String(value).padStart(2, "0");

  if (days) {
    return `${days}d ${two(hours)}h ${two(minutes)}m ${two(remainder)}s`;
  }

  if (hours) {
    return `${hours}h ${two(minutes)}m ${two(remainder)}s`;
  }

  return `${minutes}m ${two(remainder)}s`;
}

function dataRequestLiveAgeSeconds(element) {
  const initialSeconds = Number(element.dataset.initialAgeSeconds) || 0;
  const startedAt = Number(element.dataset.startedAt);

  const elapsed = Math.max(
    0,
    Math.floor((performance.now() - startedAt) / 1000)
  );

  return Math.max(0, initialSeconds + elapsed);
}

function dataRequestInstallWarRoomClock(report) {
  if (report._dataRequestWarRoomClock) {
    clearInterval(report._dataRequestWarRoomClock);
    report._dataRequestWarRoomClock = null;
  }

  const root = report.page && $(report.page.wrapper)[0];

  if (!root) {
    return;
  }

  const styleId = "data-request-war-room-live-style";

  if (!root.querySelector(`#${styleId}`)) {
    const style = document.createElement("style");
    style.id = styleId;
    style.textContent = `
      .data-request-live-age {
        font-variant-numeric: tabular-nums;
        font-weight: 600;
      }

      .data-request-live-age.is-overdue {
        color: #b91c1c;
      }

      .data-request-live-state {
        display: inline-block;
        border-radius: 999px;
        padding: 2px 9px;
        background: #e5e7eb;
        color: #374151;
        font-weight: 600;
      }

      .data-request-live-state.is-overdue {
        background: #fee2e2;
        color: #991b1b;
      }
    `;
    root.appendChild(style);
  }

  const tick = () => {
    const route = frappe.get_route();

    if (
      route[0] !== "query-report" ||
      route[1] !== DATA_REQUEST_WAR_ROOM_NAME
    ) {
      clearInterval(report._dataRequestWarRoomClock);
      report._dataRequestWarRoomClock = null;
      return;
    }

    root.querySelectorAll(
      ".data-request-live-age, .data-request-live-state"
    ).forEach((element) => {
      const seconds = dataRequestLiveAgeSeconds(element);
      const overdue = seconds >= DATA_REQUEST_OVERDUE_SECONDS;

      element.classList.toggle("is-overdue", overdue);

      if (element.classList.contains("data-request-live-age")) {
        element.textContent = dataRequestFormatAge(seconds);
      } else {
        element.textContent = overdue
          ? "OVERDUE"
          : "WITHIN 10 MIN";
      }
    });
  };

  report._dataRequestWarRoomClock = setInterval(tick, 1000);
  tick();
}

frappe.query_reports[DATA_REQUEST_WAR_ROOM_NAME] = {
  filters: [],

  onload(report) {
    dataRequestInstallWarRoomClock(report);
  },

  refresh(report) {
    dataRequestInstallWarRoomClock(report);
  },

  formatter(value, row, column, data, default_formatter) {
    if (!data) {
      return default_formatter(value, row, column, data);
    }

    if (
      column.fieldname !== "age" &&
      column.fieldname !== "age_state"
    ) {
      return default_formatter(value, row, column, data);
    }

    const seconds = Math.max(0, Number(data.age_seconds) || 0);
    const overdue = seconds >= DATA_REQUEST_OVERDUE_SECONDS;
    const cssClass = overdue ? " is-overdue" : "";

    // Use a monotonic browser clock to advance the server-provided age.
    const attributes = [
      `data-initial-age-seconds="${Math.floor(seconds)}"`,
      `data-started-at="${performance.now()}"`
    ].join(" ");

    if (column.fieldname === "age") {
      return (
        `<span class="data-request-live-age${cssClass}" ${attributes}>` +
        dataRequestFormatAge(seconds) +
        "</span>"
      );
    }

    return (
      `<span class="data-request-live-state${cssClass}" ${attributes}>` +
      (overdue ? "OVERDUE" : "WITHIN 10 MIN") +
      "</span>"
    );
  }
};
