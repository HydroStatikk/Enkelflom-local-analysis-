document.addEventListener('DOMContentLoaded', function() {
    // Toggle between file upload and example data
    const uploadDataRadio = document.getElementById('uploadData');
    const useExampleRadio = document.getElementById('useExample');
    const uploadSection = document.getElementById('uploadSection');
    const exampleDataSection = document.getElementById('exampleDataSection');
    const fileInput = document.getElementById('file');
    const useExampleDataInput = document.getElementById('useExampleData');
    
    uploadDataRadio.addEventListener('change', function() {
        if (this.checked) {
            uploadSection.classList.remove('d-none');
            exampleDataSection.classList.add('d-none');
            useExampleDataInput.value = 'false';
        }
    });
    
    useExampleRadio.addEventListener('change', function() {
        if (this.checked) {
            uploadSection.classList.add('d-none');
            exampleDataSection.classList.remove('d-none');
            useExampleDataInput.value = 'true';
            loadExampleDataPreview();
        }
    });
    
    // Load example data preview
    function loadExampleDataPreview() {
        const previewHeader = document.getElementById('previewHeader');
        const previewBody = document.getElementById('previewBody');
        const previewSection = document.getElementById('exampleDataPreview');
        
        // Fetch example data from server
        fetch('/example-data')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show preview section
                    previewSection.classList.remove('d-none');
                    
                    // Create header row
                    let headerRow = '<tr>';
                    data.columns.forEach(column => {
                        headerRow += `<th>${column}</th>`;
                    });
                    headerRow += '</tr>';
                    previewHeader.innerHTML = headerRow;
                    
                    // Create body rows (limited to 5 samples)
                    let bodyRows = '';
                    data.sample_data.forEach(row => {
                        let rowHtml = '<tr>';
                        data.columns.forEach(column => {
                            rowHtml += `<td>${row[column]}</td>`;
                        });
                        rowHtml += '</tr>';
                        bodyRows += rowHtml;
                    });
                    previewBody.innerHTML = bodyRows;
                } else {
                    previewSection.innerHTML = `<div class="alert alert-danger">Error loading example data: ${data.message}</div>`;
                }
            })
            .catch(error => {
                previewSection.innerHTML = `<div class="alert alert-danger">Error loading example data: ${error.message}</div>`;
            });
    }
    
    // Form validation
    const form = document.querySelector('form');
    form.addEventListener('submit', function(event) {
        if (uploadDataRadio.checked && (!fileInput.files || fileInput.files.length === 0)) {
            event.preventDefault();
            alert('Please select a file to upload.');
            return false;
        }
        
        // Validate numeric inputs
        const numericInputs = [
            'latitude', 'longitude', 'radius', 'catchmentArea', 
            'climateFactor', 'safetyFactor', 
            'localityScalingFactor', 'distanceScalingFactor'
        ];
        
        for (let inputId of numericInputs) {
            const input = document.getElementById(inputId);
            if (!input.value || isNaN(parseFloat(input.value))) {
                event.preventDefault();
                alert(`Please enter a valid number for ${inputId}.`);
                input.focus();
                return false;
            }
        }
        
        return true;
    });
});
