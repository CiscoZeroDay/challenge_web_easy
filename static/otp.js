fetch('/api/send_otp')
  .then(res => res.json())
  .then(data => console.log("OTP API Response:", data));  
