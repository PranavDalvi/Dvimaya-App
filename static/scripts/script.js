window.addEventListener("beforeunload", function () {
  eel.close_python();
});

// Handle Drag & Drop Upload
const dropArea = document.getElementById("drop-area");
const fileInput = document.getElementById("fileInput");
const dropText = document.getElementById("drop-text");
const resultIcon = document.getElementById("resultIcon");
const scanResult = document.getElementById("scanResult");
let scanning = true; // To track scan status

dropArea.addEventListener("click", () => {
  fileInput.click();
});

// Update file name when selected from file manager
fileInput.addEventListener("change", function () {
  if (fileInput.files.length > 0) {
    dropText.innerText = fileInput.files[0].name;
  }
});

dropArea.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropArea.style.borderColor = "white";
});

dropArea.addEventListener("dragleave", () => {
  dropArea.style.borderColor = "#36454f";
});

dropArea.addEventListener("drop", (event) => {
  event.preventDefault();
  dropArea.style.borderColor = "#36454f";

  let files = event.dataTransfer.files;
  if (files.length > 0) {
    fileInput.files = files;
  }
});

function showPage(pageId) {
  document.querySelectorAll(".page").forEach((page) => {
    page.classList.remove("active");
  });
  document.getElementById(pageId).classList.add("active");
}

function startScanning() {
  const fileInput = document.getElementById("fileInput").files[0];

  if (!fileInput) {
    alert("Please select a file.");
    return;
  }

  // Move to Scanning Page
  showPage("scanningPage");

  // Read file and send to Python for scanning
  const reader = new FileReader();
  reader.onload = function (event) {
    const fileData = event.target.result;
    eel.save_temp_file(
      fileInput.name,
      fileData
    )(function (response) {
      console.log(response);
      if (response) {
        eel.generate_visualization(response)(function (prediction) {
          console.log(prediction);
          if (prediction === "Safe") {
            resultIcon.src = "assets/safe.svg"; // Green check icon
            scanResult.innerText = "Safe";
          } else {
            resultIcon.src = "assets/risky.svg"; // Red skull icon
            scanResult.innerText = "Risky";
          }

          // Move to Results Page
          showPage("resultsPage");
        });
      } else {
        console.log("Error: " + response);
      }
    });
  };
  reader.readAsDataURL(fileInput);
}

// Simulate Scanning Progress
function updateScanningProgress() {
  let percentage = 0;
  let interval = setInterval(() => {
    if (!scanning) {
      clearInterval(interval);
      return;
    }
    percentage += 10;
    document.getElementById("scanPercentage").innerText = percentage + "%";
    if (percentage >= 100) {
      clearInterval(interval);
    }
  }, 500);
}

// Cancel Scan
function cancelScan() {
  eel.cancel_scan()(function (response) {
    console.log(response); // Log response
    showPage("uploadPage"); // Go back to upload page
  });
}
