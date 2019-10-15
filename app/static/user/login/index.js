$(document).ready(function() {
  
  var animating = false,
      submitPhase1 = 1100,
      submitPhase2 = 400,
      logoutPhase1 = 800,
      $login = $(".login"),
      $app = $(".app");
  
  function ripple(elem, e) {
    $(".ripple").remove();
    var elTop = elem.offset().top,
        elLeft = elem.offset().left,
        x = e.pageX - elLeft,
        y = e.pageY - elTop;
    var $ripple = $("<div class='ripple'></div>");
    $ripple.css({top: y, left: x});
    elem.append($ripple);
  };
  
  $(document).on("click", ".login__submit", function(e) {
    if (animating) return;
    animating = true;
    var that = this;
    ripple($(that), e);
    $(that).addClass("processing");
    var activity_code = $(".activity_code").val();
    console.log(activity_code);
    console.log(activity_code.length);
    if (activity_code.length<20) {
      layer.msg("卡密格式不正确，请重新输入");
       $(that).removeClass("processing");
       animating = false;
      return;
    }else{
      $.post("/index.php/Returndata/return_detect_type_url",{activity_code:activity_code},function(result){
        result = $.parseJSON(result);
        switch(result.code)
        {
          case 100:
            setTimeout(function(){
              $(that).addClass("success");
              setTimeout(function(){
                  window.location.href = result.url;
              },1000);
              
            },2000);
            
            break;
          case 500:
            alert('为了提高爆粉效果,暂时关闭，技术调整');
            setTimeout(function(){
                  window.location.reload()
              },1000);
            return false;
            break;
          default:
            layer.msg(result.msg);
            $(that).removeClass("processing");
            animating = false;
            break;
        }
        return;
      });
    }
    
    // setTimeout(function() {
    //   $(that).addClass("success");
    //   setTimeout(function() {
    //     $app.show();
    //     $app.css("top");
    //     $app.addClass("active");
    //   }, submitPhase2 - 70);
    //   setTimeout(function() {
    //     $login.hide();
    //     $login.addClass("inactive");
    //     animating = false;
    //     $(that).removeClass("success processing");
    //   }, submitPhase2);
    // }, submitPhase1);
  });
  
  $(document).on("click", ".app__logout", function(e) {
    if (animating) return;
    $(".ripple").remove();
    animating = true;
    var that = this;
    $(that).addClass("clicked");
    setTimeout(function() {
      $app.removeClass("active");
      $login.show();
      $login.css("top");
      $login.removeClass("inactive");
    }, logoutPhase1 - 120);
    setTimeout(function() {
      $app.hide();
      animating = false;
      $(that).removeClass("clicked");
    }, logoutPhase1);
  });
  
});