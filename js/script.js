let SERVER = "192.168.1.218";
let PORT = "8082";


function upload_files(btn) {
    const input_file = document.getElementById("input_file");
  
    const formData = new FormData();
  
    formData.append("folder_name", btn.value);
  
    for (const file of input_file.files) {
      formData.append("size_img", file.size);
      formData.append("file_img", file);
    }
  
    fetch("http://" + SERVER + ":" + PORT, {
      mode: "no-cors",
      method: "post",
      body: formData,
    })
    .catch((error) => ("Uploading files failed!", error));
  }