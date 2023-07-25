// Requires boost
// // TP build from MATLAB: (with boost headers in named directory)
//mex -Iboost_1_82_0 -R2018a mat2py.cpp
//
#include "mex.h"
#include "matrix.h"

//#include <boost\interprocess\shared_memory_object.hpp>
#include "boost\interprocess\windows_shared_memory.hpp"
#include "boost\interprocess\mapped_region.hpp"
//#include <opencv2/opencv.hpp>
#include <numeric>
#include <vector>
#include <iostream> // debugging
    
#include <boost/asio.hpp>


using namespace boost::asio;

using ip::tcp;
using namespace boost::interprocess;
using namespace std;

# define PORT 50000
int socket_message(std::string message);

// To put to stdio
class mystream : public std::streambuf
{
protected:
virtual std::streamsize xsputn(const char *s, std::streamsize n) { mexPrintf("%.*s", n, s); return n; }
virtual int overflow(int c=EOF) { if (c != EOF) { mexPrintf("%.1s", &c); } return 1; }
};
class scoped_redirect_cout
{
public:
  scoped_redirect_cout() { old_buf = std::cout.rdbuf(); std::cout.rdbuf(&mout); }
  ~scoped_redirect_cout() { std::cout.rdbuf(old_buf); }
private:
  mystream mout;
  std::streambuf *old_buf;
};
static scoped_redirect_cout mycout_redirect;
// https://www.mathworks.com/matlabcentral/answers/132527-in-mex-files-where-does-output-to-stdout-and-stderr-go


int arrayProduct(vector<int>& v) {
        return accumulate(v.begin(), v.end(), 1, multiplies<int>());
    };

void mexFunction(int nlhs, mxArray *plhs[], int nrhs, const mxArray *prhs[])
{
    mwSize ndims=mxGetNumberOfDimensions(prhs[0]);
    const mwSize* dim_vol = mxGetDimensions(prhs[0]);
    const mxSingle* p_vol = mxGetSingles(prhs[0]);
    int len=4; // sizeof single
    
    // Make string with list of dimensions. SO annoying in C++
    std::string message;
    message = "send ";
    
    for (int ndim=int(ndims)-1; ndim>=0; ndim--) {
        char buff[16];
        len *= int(dim_vol[ndim]);
        snprintf(buff, sizeof(buff), "%d", int(dim_vol[ndim]));
        message += buff;
        if (ndim>0)
            message += ',';
    }
    cout << len << " " << message;
    //cout << ndims << dim_vol[0] << dim_vol[1]; //<< arrayProduct(&dim_vol);
    
windows_shared_memory shmem(open_or_create, "shm", read_write, len);

mapped_region region(shmem, read_write);

float* dest_ptr = static_cast<float*> (region.get_address());

for (int i=0; i<len/4; i++) {
    dest_ptr[i] = float(p_vol[i]);
};
//std::memcpy(img_ptr , imgMat.data, img_size);

socket_message(message); // will block until sent

// TODO: Ideally we get a response from the "server" saying it received the data
//std::system("pause");
}

int socket_message(std::string message)
{
    #include <chrono>
    #include <thread>
 
     boost::asio::io_service io_service;
//socket creation
     tcp::socket socket(io_service);
//connection
     boost::system::error_code error;
     
   
     socket.connect( tcp::endpoint( boost::asio::ip::address::from_string("127.0.0.1"), PORT ));
// request/message from client
     socket.set_option(boost::asio::socket_base::reuse_address(true), error);
    if (error)
    {
        cerr << "socket.set error: " << error.message() << endl;
    }  
     
     boost::asio::write( socket, boost::asio::buffer(message), error );
     cout << error;
     
    for( int retries=0; (socket.is_open() && socket.available() < 1 && retries<5 ); retries+=1) {
        //cerr << "waiting to shutdown... ";
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
     }
     
     socket.shutdown(boost::asio::ip::tcp::socket::shutdown_both, error);
    if (error)
    {
        cerr << "socket.shutdown error: " << error.message() << endl;
    }

    socket.close(error);
    if (error)
    {
        cerr << "socket.close error: " << error.message() << endl;
    }     

}

#if 0

//#include <arpa/inet.h>
#include <stdio.h>
#include <string.h>
#include <socket.h>
#include <unistd.h>

int socket_message()
{
    int status, valread, client_fd;
    struct sockaddr_in serv_addr;
    char* hello = "send 10,20,30";
    char buffer[1024] = { 0 };
    if ((client_fd = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
        printf("\n Socket creation error \n");
        return -1;
    }
  
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(PORT);
  
    // Convert IPv4 and IPv6 addresses from text to binary
    // form
    if (inet_pton(AF_INET, "127.0.0.1", &serv_addr.sin_addr)
        <= 0) {
        printf(
            "\nInvalid address/ Address not supported \n");
        return -1;
    }
  
    if ((status
         = connect(client_fd, (struct sockaddr*)&serv_addr,
                   sizeof(serv_addr)))
        < 0) {
        printf("\nConnection Failed \n");
        return -1;
    }
    send(client_fd, hello, strlen(hello), 0);
    printf("Hello message sent\n");
    valread = read(client_fd, buffer, 1024);
    printf("%s\n", buffer);
  
    // closing the connected socket
    close(client_fd);
}

#endif //0
